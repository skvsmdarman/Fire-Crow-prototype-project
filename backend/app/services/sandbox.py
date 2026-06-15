import logging
import os
from typing import List, Tuple, Any

from app.config import settings
from app.services.redaction import redact_text, truncate_text

logger = logging.getLogger("firecrow.services.sandbox")

# Try importing docker SDK
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False


class SandboxManager:
    """
    Manages isolated Docker pentesting environments.
    Spins up private bridge networks, mounts/deploys the cloned app target,
    deploys a Kali container inside the network, and exposes command execution hooks.
    Falls back to high-fidelity simulated containers if Docker daemon is not active.
    """
    client: Any
    mock_mode: bool
    unavailable_reason: str

    def __init__(self):
        self.client = None
        self.mock_mode = False
        self.unavailable_reason = ""
        
        if settings.FIRE_CROW_MOCK_SANDBOX:
            if not settings.DEBUG:
                raise RuntimeError("FIRE_CROW_MOCK_SANDBOX is not allowed in production (DEBUG=False).")
            self.mock_mode = True
            logger.info("FIRE_CROW_MOCK_SANDBOX is enabled. Running in sandbox simulation mode (DEBUG only).")
        elif DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()  # type: ignore
                # Ping daemon to confirm it is actually running and responsive
                self.client.ping()
                logger.info("Docker daemon connected. Sandbox manager running in active mode.")
            except Exception as e:
                self.unavailable_reason = "Docker daemon is unavailable."
                if settings.DEBUG:
                    self.mock_mode = True
                    logger.warning(
                        "Could not connect to Docker daemon: %s. Falling back to DEBUG simulation mode.",
                        redact_text(str(e)),
                    )
                else:
                    logger.error("Docker daemon unavailable in production; refusing sandbox simulation.", exc_info=True)
                    raise RuntimeError("Docker daemon is required for sandbox operations in production.")
        else:
            self.unavailable_reason = "Docker python SDK is not installed."
            if settings.DEBUG:
                self.mock_mode = True
                logger.warning("Docker python SDK not installed. Running in DEBUG simulation mode.")
            else:
                logger.error("Docker python SDK missing in production; refusing sandbox simulation.")
                raise RuntimeError("Docker python SDK is required for sandbox operations in production.")

    def _container_security_options(self, job_id: str, role: str) -> dict[str, Any]:
        return {
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "mem_limit": "512m",
            "nano_cpus": 500000000,
            "pids_limit": 100,
            "read_only": True,
            "tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},
            "privileged": False,
            "labels": {
                "firecrow.job_id": job_id,
                "firecrow.role": role,
            },
        }

    def _detect_launch_profile(self, clone_path: str) -> Tuple[str, str, int, str]:
        """
        Detects the profile of the cloned repository.
        Returns: (profile_name, image_name, port, start_command)
        """
        if not clone_path or not os.path.exists(clone_path):
            return "unsupported", "", 0, ""

        # Node / Next.js
        if os.path.exists(os.path.join(clone_path, "package.json")):
            return "node", settings.SANDBOX_NODE_IMAGE, 3000, "npm run start"

        # Python / Django / FastAPI / Flask
        has_python = False
        for filename in ("requirements.txt", "main.py", "app.py", "wsgi.py", "manage.py"):
            if os.path.exists(os.path.join(clone_path, filename)):
                has_python = True
                break

        if has_python:
            if os.path.exists(os.path.join(clone_path, "manage.py")):
                return "django", settings.SANDBOX_PYTHON_IMAGE, 8000, "python manage.py runserver 0.0.0.0:8000"
            return "python", settings.SANDBOX_PYTHON_IMAGE, 8000, "python -m http.server 8000"

        return "unsupported", "", 0, ""

    def provision_sandbox(
        self, 
        job_id: str, 
        clone_path: str, 
        entry_points: List[str]
    ) -> Tuple[bool, str, str, str, str]:
        """
        Provisions private bridge network, target application container, and Kali testing container.
        Returns: Tuple of (success, network_name, target_container_id, kali_container_id, kali_ip)
        """
        net_name = f"fc-net-{job_id}"
        target_cid = f"fc-target-{job_id}"
        kali_cid = f"fc-kali-{job_id}"
        kali_ip = "172.20.0.5"

        if self.mock_mode:
            if not settings.DEBUG:
                raise RuntimeError("Sandbox simulation mode is not allowed in production.")
            logger.info(f"[SIMULATOR] Created virtual private bridge network '{net_name}'")
            profile_name, _, _, _ = self._detect_launch_profile(clone_path)
            if profile_name == "unsupported":
                logger.warning("[SIMULATOR] Unsupported repository tech stack; skipped target container run.")
                target_cid_sim = ""
            else:
                logger.info(f"[SIMULATOR] Deployed target application container '{target_cid}' with path '{clone_path}' (profile: {profile_name})")
                target_cid_sim = target_cid
            logger.info(f"[SIMULATOR] Deployed Kali pentest agent container '{kali_cid}' connected to private network.")
            return True, net_name, target_cid_sim, kali_cid, kali_ip

        if not self.client:
            logger.error("Docker client not initialized. %s", self.unavailable_reason)
            if settings.DEBUG:
                self.mock_mode = True
                logger.warning("Falling back to DEBUG simulation mode due to missing Docker client.")
                return self.provision_sandbox(job_id, clone_path, entry_points)
            raise RuntimeError("Docker client is required for sandbox operations in production.")

        client = self.client

        try:
            # 1. Create docker bridge network
            network = client.networks.create(net_name, driver="bridge")

            # 2. Start target application container
            has_dockerfile = any("Dockerfile" in ep for ep in entry_points) and os.path.exists(os.path.join(clone_path, "Dockerfile"))
            
            target_container_id_str = ""
            profile_name, image_name, port, start_command = self._detect_launch_profile(clone_path)
            
            if profile_name == "unsupported":
                logger.warning("Unsupported repository tech stack for active sandbox test; skipped target container run.")
            else:
                # User Dockerfile builds are permanently disabled for security.
                if has_dockerfile:
                    logger.info(
                        "Repository Dockerfile detected for job %s but user Dockerfile builds are disabled; using controlled runtime image.",
                        job_id,
                    )
                command = start_command

                # Run target app container
                target_container = client.containers.run(
                    image_name,
                    name=target_cid,
                    detach=True,
                    network=net_name,
                    command=command,
                    volumes={clone_path: {"bind": "/app", "mode": "ro"}},
                    working_dir="/app",
                    **self._container_security_options(job_id, "target"),
                )
                target_container_id_str = str(target_container.id or "")

            # 3. Start Kali pentest container
            # We use a custom slim Kali Linux image equipped with security audit tools (nmap, sqlmap, curl, etc.)
            kali_container = client.containers.run(
                settings.FIRE_CROW_SCANNER_IMAGE,
                name=kali_cid,
                detach=True,
                network=net_name,
                tty=True,
                command="sleep infinity",
                **self._container_security_options(job_id, "scanner"),
            )

            logger.info(f"Docker sandbox successfully provisioned for job {job_id}.")
            
            # Inspect Kali container network settings to retrieve private IP address
            kali_container.reload()
            net_settings = kali_container.attrs["NetworkSettings"]["Networks"].get(net_name, {})
            ip_address = net_settings.get("IPAddress", kali_ip)

            return True, net_name, target_container_id_str, str(kali_container.id or ""), str(ip_address or "")

        except Exception as e:
            logger.exception("Failed to provision docker containers: %s", redact_text(str(e)))
            # Try to cleanup partially created resources
            self.cleanup_sandbox(net_name, target_cid, kali_cid)
            return False, "", "", "", ""

    def execute_kali_command(self, kali_container_id: str, command: List[str]) -> Tuple[int, str]:
        """Runs a command inside the Kali agent container and returns the status code and stdout/stderr."""
        allowed_executables = {"nmap", "sqlmap", "nuclei", "curl", "osv-scanner", "trivy", "semgrep"}
        if not command or not all(isinstance(part, str) for part in command):
            return 126, "Command rejected: expected a non-empty list of strings."

        executable = os.path.basename(command[0])
        if executable not in allowed_executables:
            if not settings.DEBUG:
                return 126, "Command rejected by scanner allowlist."
            logger.warning("DEBUG mode allowing non-standard scanner command: %s", executable)

        if self.mock_mode:
            logger.warning(f"Simulated executing Kali command has been disabled to preserve demo integrity. Tool unavailable: {' '.join(command)}")
            return 1, "Tool execution unavailable."

        if not self.client:
            return 1, "Docker client not initialized"

        client = self.client

        try:
            container = client.containers.get(kali_container_id)
            result = container.exec_run(command)
            
            # exec_run returns tuple[int | None, bytes | Iterator[bytes]]
            exit_code = int(result[0]) if result[0] is not None else 0
            output_bytes = result[1]
            
            if hasattr(output_bytes, "decode"):
                output_str = output_bytes.decode("utf-8", errors="ignore")
            elif isinstance(output_bytes, bytes):
                output_str = output_bytes.decode("utf-8", errors="ignore")
            elif isinstance(output_bytes, str):
                output_str = output_bytes
            else:
                output_str = str(output_bytes)

            return exit_code, truncate_text(redact_text(output_str), max_length=12000)
        except Exception as e:
            logger.error("Failed to execute command in scanner container: %s", redact_text(str(e)))
            return 1, "Command execution error"

    def cleanup_sandbox(self, network_name: str, target_container_id: str, kali_container_id: str):
        """Removes the target container, Kali container, and bridge network."""
        if self.mock_mode:
            logger.info(f"[SIMULATOR] Cleaned up network '{network_name}', container '{target_container_id}', and container '{kali_container_id}'")
            return

        if not self.client:
            return

        client = self.client

        # Stop and remove containers
        for cid in (target_container_id, kali_container_id):
            if cid:
                try:
                    container = client.containers.get(cid)
                    container.stop(timeout=5)
                    container.remove(force=True)
                    logger.info(f"Removed container {cid}")
                except Exception as e:
                    logger.warning(f"Failed to remove container {cid}: {str(e)}")

        # Remove bridge network
        if network_name:
            try:
                network = client.networks.get(network_name)
                network.remove()
                logger.info(f"Removed network {network_name}")
            except Exception as e:
                logger.warning(f"Failed to remove network {network_name}: {str(e)}")
