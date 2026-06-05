from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
BACKEND_ENV = ROOT / ".venv" / "Scripts" / "python.exe"


def resolve_python() -> str:
    if BACKEND_ENV.exists():
        return str(BACKEND_ENV)
    return sys.executable


def resolve_npm() -> str:
    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        npm_cmd = shutil.which("npm.cmd")
    if not npm_cmd:
        raise RuntimeError("npm was not found in PATH. Install Node.js or run the commands manually.")
    return npm_cmd


def resolve_npx() -> str:
    npx_cmd = shutil.which("npx")
    if not npx_cmd:
        npx_cmd = shutil.which("npx.cmd")
    if not npx_cmd:
        raise RuntimeError("npx was not found in PATH. Install Node.js or run the commands manually.")
    return npx_cmd


def run_step(name: str, command: list[str], cwd: Path, env: dict[str, str] | None = None) -> bool:
    print(f"\n==========================================")
    print(f"Running step: {name}")
    print(f"Command: {' '.join(command)}")
    print(f"CWD: {cwd}")
    print(f"==========================================")
    
    try:
        res = subprocess.run(command, cwd=cwd, env=env)
        if res.returncode != 0:
            print(f"\n[FAIL] Step '{name}' failed with exit code {res.returncode}.", file=sys.stderr)
            return False
        print(f"\n[PASS] Step '{name}' succeeded!")
        return True
    except Exception as e:
        print(f"\n[ERROR] Exception occurred while running step '{name}': {str(e)}", file=sys.stderr)
        return False


def main() -> int:
    python_cmd = resolve_python()
    npm_cmd = resolve_npm()
    npx_cmd = resolve_npx()
    
    # Resolve pytest path
    pytest_candidates = [
        str(ROOT / ".venv" / "Scripts" / "pytest.exe"),
        str(ROOT / ".venv" / "bin" / "pytest"),
        "pytest"
    ]
    pytest_cmd = "pytest"
    for candidate in pytest_candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            pytest_cmd = candidate
            break

    # Step 1: Frontend Linting
    if not run_step("Frontend Linting", [npm_cmd, "run", "lint"], FRONTEND_DIR):
        return 1

    # Step 2: Frontend Building
    if not run_step("Frontend Build", [npm_cmd, "run", "build"], FRONTEND_DIR):
        return 1

    # Step 3: Backend Type-Checking (Pyright)
    if not run_step("Backend Type-Checking (Pyright)", [npx_cmd, "pyright", "--pythonpath", python_cmd], ROOT):
        return 1

    # Step 4: Backend Unit Testing (Pytest)
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(ROOT)
    if not run_step("Backend Unit Tests (Pytest)", [pytest_cmd, "backend/tests/"], ROOT, env=test_env):
        return 1

    print("\n[SUCCESS] All checks passed successfully (Frontend lint, build, Backend type-checking, and tests)!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
