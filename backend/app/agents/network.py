import logging
import re
from typing import List, Dict, Any
from backend.app.services.sandbox import SandboxManager

logger = logging.getLogger("firecrow.agents.network")


def run_network_scan(kali_container_id: str, target_host: str) -> List[Dict[str, Any]]:
    """
    Runs an active Nmap port and service signature scan against the target app
    inside the Kali container.
    """
    logger.info(f"Initiating network scanner targeting {target_host}")
    
    # We scan all ports from 1 to 10000 plus common web ports
    command = ["nmap", "-sV", "-p", "80,443,3000,5000,8000,8080", target_host]
    
    manager = SandboxManager()
    exit_code, output = manager.execute_kali_command(kali_container_id, command)
    
    if exit_code != 0:
        logger.error(f"Nmap scan exited with code {exit_code}: {output}")
        return []

    logger.info("Nmap scan completed. Parsing results...")
    
    open_ports = []
    # Regex parser for Nmap output lines like:
    # 8000/tcp open  http    BaseHTTP 0.6 (Python 3.12.1)
    port_pattern = re.compile(r"(\d+)/tcp\s+(\w+)\s+(\S+)(?:\s+(.*))?")

    for line in output.splitlines():
        match = port_pattern.search(line)
        if match:
            port = int(match.group(1))
            state = match.group(2)
            service = match.group(3)
            version = match.group(4) or "unknown"
            
            if state == "open":
                open_ports.append({
                    "port": port,
                    "service": service,
                    "version": version.strip()
                })

    logger.info(f"Discovered {len(open_ports)} open services: {open_ports}")
    return open_ports
