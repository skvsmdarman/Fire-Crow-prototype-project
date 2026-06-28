from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import IO
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
BACKEND_ENV = ROOT / ".venv" / "Scripts" / "python.exe"


class ManagedProcess:
    def __init__(self, name: str, command: list[str], cwd: Path, env: dict[str, str] | None = None):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.env = env
        self.process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        assert self.process.stdout is not None
        self._thread = threading.Thread(target=self._stream_output, args=(self.process.stdout,), daemon=True)
        self._thread.start()

    def _stream_output(self, stream: IO[str]) -> None:
        prefix = f"[{self.name}]"
        for line in iter(stream.readline, ""):
            safe_line = f"{prefix} {line.rstrip()}".encode("utf-8", errors="replace").decode("utf-8")
            print(
                safe_line.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"),
                flush=True,
            )
        stream.close()

    def terminate(self) -> None:
        if not self.process or self.process.poll() is not None:
            return

        try:
            if os.name == "nt":
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.terminate()
            self.process.wait(timeout=8)
        except Exception:
            self.process.kill()
            self.process.wait(timeout=5)


class ExistingService(ManagedProcess):
    def __init__(self, name: str, url: str):
        super().__init__(name=name, command=[f"reuse {url}"], cwd=ROOT)
        self.url = url

    def start(self) -> None:
        print(f"[launcher] reusing existing {self.name} at {self.url}", flush=True)

    def terminate(self) -> None:
        return


def can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, URLError):
        return False


def can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind((host, port))
            return True
    except OSError:
        return False


def find_free_port(start_port: int, *, host: str = "127.0.0.1", max_attempts: int = 50) -> int:
    for port in range(start_port, start_port + max_attempts):
        if not can_connect(host, port) and can_bind(host, port):
            return port
    raise RuntimeError(f"No free port found from {start_port} through {start_port + max_attempts - 1}.")


def resolve_python() -> str:
    if BACKEND_ENV.exists():
        return str(BACKEND_ENV)
    return sys.executable


def resolve_npm() -> str:
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        raise RuntimeError("npm was not found in PATH. Install Node.js or run the frontend manually.")
    return npm_cmd


def build_processes(
    skip_worker: bool,
    backend_port: int,
    frontend_port: int,
    *,
    reuse_backend: bool,
    reuse_frontend: bool,
) -> list[ManagedProcess]:
    python_cmd = resolve_python()
    npm_cmd = resolve_npm()

    backend_env = os.environ.copy()
    backend_env.setdefault("PYTHONPATH", str(ROOT))
    backend_env["PORT"] = str(backend_port)

    frontend_env = os.environ.copy()
    frontend_env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{backend_port}/api/v1"

    backend_process: ManagedProcess
    if reuse_backend:
        backend_process = ExistingService("backend", f"http://localhost:{backend_port}")
    else:
        backend_process = ManagedProcess(
            name="backend",
            command=[
                python_cmd,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(backend_port),
                "--reload",
            ],
            cwd=ROOT,
            env=backend_env,
        )

    frontend_process: ManagedProcess
    if reuse_frontend:
        frontend_process = ExistingService("frontend", f"http://localhost:{frontend_port}")
    else:
        frontend_process = ManagedProcess(
            name="frontend",
            command=[npm_cmd, "run", "dev", "--", "--port", str(frontend_port)],
            cwd=FRONTEND_DIR,
            env=frontend_env,
        )

    processes = [backend_process, frontend_process]

    if not skip_worker:
        worker_env = backend_env.copy()
        worker_env.setdefault("FIRE_CROW_MOCK_SANDBOX", "True")
        processes.append(
            ManagedProcess(
                name="worker",
                command=[
                    python_cmd,
                    "-m",
                    "celery",
                    "-A",
                    "backend.app.workers.celery_app:celery_app",
                    "worker",
                    "--loglevel=info",
                    "--pool=solo",
                ],
                cwd=ROOT,
                env=worker_env,
            )
        )

    return processes


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        load_dotenv(ROOT / ".env.local", override=True)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="Start Fire Crow frontend, backend, and optional worker together.")
    parser.add_argument("--skip-worker", action="store_true", help="Do not start the Celery worker.")
    parser.add_argument("--backend-port", type=int, default=8000, help="Preferred backend port. Falls forward if busy.")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Preferred frontend port. Falls forward if busy.")
    args = parser.parse_args()

    reuse_backend = http_ok(f"http://localhost:{args.backend_port}/health")
    if reuse_backend:
        backend_port = args.backend_port
    else:
        backend_port = find_free_port(args.backend_port)

    reuse_frontend = http_ok(f"http://localhost:{args.frontend_port}/")
    if reuse_frontend:
        frontend_port = args.frontend_port
    else:
        frontend_port = find_free_port(args.frontend_port)

    if backend_port != args.backend_port:
        print(f"[launcher] backend port {args.backend_port} is unavailable. Using {backend_port}.", flush=True)
    if frontend_port != args.frontend_port:
        print(f"[launcher] frontend port {args.frontend_port} is unavailable. Using {frontend_port}.", flush=True)

    skip_worker = args.skip_worker or not can_connect("127.0.0.1", 6379)
    if skip_worker and not args.skip_worker:
        print("[launcher] Redis was not reachable on 127.0.0.1:6379. Starting without Celery worker; API fallback mode remains available.", flush=True)

    print(f"[launcher] frontend will call API at http://localhost:{backend_port}/api/v1", flush=True)
    processes = build_processes(
        skip_worker=skip_worker,
        backend_port=backend_port,
        frontend_port=frontend_port,
        reuse_backend=reuse_backend,
        reuse_frontend=reuse_frontend,
    )

    try:
        for managed in processes:
            print(f"[launcher] starting {managed.name}: {' '.join(managed.command)}", flush=True)
            managed.start()

        while True:
            for managed in processes:
                if managed.process and managed.process.poll() is not None:
                    print(f"[launcher] {managed.name} exited with code {managed.process.returncode}. Shutting down the rest.", flush=True)
                    return managed.process.returncode or 0
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\n[launcher] stopping services...", flush=True)
        return 0
    finally:
        for managed in reversed(processes):
            managed.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
