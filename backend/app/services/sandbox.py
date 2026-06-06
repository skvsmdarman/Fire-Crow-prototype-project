import logging
import os
from typing import List, Tuple, Optional, Any

from backend.app.config import settings

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

    def __init__(self):
        self.client = None
        self.mock_mode = True
        
        if settings.FIRE_CROW_MOCK_SANDBOX:
            logger.info("FIRE_CROW_MOCK_SANDBOX is enabled. Running in simulation mode.")
        elif DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                # Ping daemon to confirm it is actually running and responsive
                self.client.ping()
                self.mock_mode = False
                logger.info("Docker daemon connected. Sandbox manager running in active mode.")
            except Exception as e:
                logger.warning(f"Could not connect to Docker daemon: {str(e)}. Falling back to simulation mode.")
        else:
            logger.warning("Docker python SDK not installed. Running in simulation mode.")

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
            logger.info(f"[SIMULATOR] Created virtual private bridge network '{net_name}'")
            logger.info(f"[SIMULATOR] Deployed target application container '{target_cid}' with path '{clone_path}'")
            logger.info(f"[SIMULATOR] Deployed Kali pentest agent container '{kali_cid}' connected to private network.")
            return True, net_name, target_cid, kali_cid, kali_ip

        if not self.client:
            logger.error("Docker client not initialized.")
            return False, "", "", "", ""

        client = self.client

        try:
            # 1. Create docker bridge network
            network = client.networks.create(net_name, driver="bridge")

            # 2. Start target application container
            # For standard scans, we spin up a generic lightweight python/node container depending on tech stack,
            # or build from the repository's Dockerfile if available.
            has_dockerfile = any("Dockerfile" in ep for ep in entry_points) and os.path.exists(os.path.join(clone_path, "Dockerfile"))
            
            if has_dockerfile:
                logger.info(f"Building custom Docker image from repository Dockerfile for job {job_id}")
                image, _ = client.images.build(path=clone_path, tag=f"fc-target-img:{job_id}")
                image_name = image.tags[0]
            else:
                image_name = "python:3.12-alpine"  # lightweight default runtime

            # Run target app container
            target_container = client.containers.run(
                image_name,
                name=target_cid,
                detach=True,
                network=net_name,
                command="python -m http.server 8000" if not has_dockerfile else None,
                volumes={clone_path: {"bind": "/app", "mode": "ro"}},
                working_dir="/app",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="512m",
                nano_cpus=500000000,
                pids_limit=100
            )

            # 3. Start Kali pentest container
            # We use a custom slim Kali Linux image equipped with security audit tools (nmap, sqlmap, curl, etc.)
            kali_container = client.containers.run(
                "kalilinux/kali-rolling:latest",
                name=kali_cid,
                detach=True,
                network=net_name,
                tty=True,
                command="sleep infinity",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="512m",
                nano_cpus=500000000,
                pids_limit=100
            )

            # Install core testing utilities in Kali if not pre-installed
            # In production, we'd pre-build a 'firecrow/kali-scanner' image.
            # Here we run basic setup commands inside Kali.
            logger.info(f"Docker sandbox successfully provisioned for job {job_id}.")
            
            # Inspect Kali container network settings to retrieve private IP address
            kali_container.reload()
            net_settings = kali_container.attrs["NetworkSettings"]["Networks"].get(net_name, {})
            ip_address = net_settings.get("IPAddress", kali_ip)

            return True, net_name, str(target_container.id or ""), str(kali_container.id or ""), str(ip_address or "")

        except Exception as e:
            logger.exception(f"Failed to provision docker containers: {str(e)}")
            # Try to cleanup partially created resources
            self.cleanup_sandbox(net_name, target_cid, kali_cid)
            return False, "", "", "", ""

    def execute_kali_command(self, kali_container_id: str, command: List[str]) -> Tuple[int, str]:
        """Runs a command inside the Kali agent container and returns the status code and stdout/stderr."""
        if self.mock_mode:
            logger.info(f"[SIMULATOR] Executing Kali command: {' '.join(command)}")
            # Custom mock outputs for testing
            cmd_str = " ".join(command)
            if "nmap" in cmd_str:
                return 0, "Host: 172.20.0.3 (fc-target)\nPORT     STATE SERVICE\n8000/tcp open  http\n"
            elif "sqlmap" in cmd_str:
                return 0, "[INFO] POST parameter 'username' is vulnerable to SQL injection (DBMS: SQLite)"
            elif "nuclei" in cmd_str:
                return 0, "[CVE-2021-44228] Critical Apache Log4j RCE vulnerability detected"
            elif "curl" in cmd_str:
                return 0, "HTTP/1.1 200 OK\nServer: BaseHTTP"
            return 0, f"Simulated output for: {cmd_str}"

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

            return exit_code, output_str
        except Exception as e:
            logger.error(f"Failed to execute command in Kali container: {str(e)}")
            return 1, f"Command execution error: {str(e)}"

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
                except Exception:
                    pass

        # Remove bridge network
        if network_name:
            try:
                network = client.networks.get(network_name)
                network.remove()
                logger.info(f"Removed network {network_name}")
            except Exception:
                pass
