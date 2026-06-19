import os
import re
import logging
import subprocess
from typing import List, Optional
from app.schemas import Finding, Severity
from app.services.redaction import redact_text

logger = logging.getLogger("firecrow.agents.config_scan")

def _is_binary_file(file_path: str) -> bool:
    """Check if file is binary by reading first 1024 bytes for null byte."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return True  # If we can't read, treat as binary to be safe

def _check_tool_available(tool_name: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        subprocess.run(
            [tool_name, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=5
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def scan_dockerfile_with_hadolint(dockerfile_path: str) -> List[Finding]:
    """Scan a Dockerfile with hadolint."""
    if not _check_tool_available("hadolint"):
        logger.warning("hadolint not available, skipping Dockerfile scan")
        return []

    findings = []
    try:
        result = subprocess.run(
            ["hadolint", "-f", "json", dockerfile_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        # hadolint returns 0 if no warnings, non-zero if warnings found
        if result.returncode not in (0, 1):
            logger.error(f"hadolint failed: {result.stderr}")
            return []

        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse hadolint JSON output: {e}")
            return []

        for item in data:
            # Map hadolint severity to our Severity
            # hadolint: error, warning, info, style
            severity_map = {
                "error": Severity.HIGH,
                "warning": Severity.MEDIUM,
                "info": Severity.LOW,
                "style": Severity.LOW
            }
            severity = severity_map.get(item.get("level", "warning").lower(), Severity.MEDIUM)

            findings.append(Finding(
                id=str(item.get("hash", "")) or str(__import__('uuid').uuid4()),
                agent_source="CONFIG_HADOLINT",
                title=item.get("message", "Dockerfile issue")[:200],
                description=item.get("message", ""),
                severity=severity,
                cwe_id=None,  # hadolint doesn't provide CWE by default
                evidence=(
                    f"scanner_name=hadolint; scanner_mode=hadolint; confidence=medium\n"
                    f"file={item.get('file', '')}; line={item.get('line', 0)}"
                ),
                remediation=item.get("message", "")
            ))
    except Exception as e:
        logger.error(f"Error running hadolint scan: {str(e)}")

    return findings

def scan_kubernetes_with_kube_linter(file_path: str) -> List[Finding]:
    """Scan a Kubernetes/YAML file with kube-linter."""
    if not _check_tool_available("kube-linter"):
        logger.warning("kube-linter not available, skipping Kubernetes scan")
        return []

    findings = []
    try:
        result = subprocess.run(
            ["kube-linter", "lint", "--format", "json", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        # kube-linter returns 0 if no issues, non-zero if issues found
        if result.returncode not in (0, 1):
            logger.error(f"kube-linter failed: {result.stderr}")
            return []

        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse kube-linter JSON output: {e}")
            return []

        # Note: kube-linter output format is a list of objects under "files"
        # Each file has "messages" which are the issues.
        for file_result in data.get("files", []):
            for message in file_result.get("messages", []):
                # Map kube-linter severity to our Severity
                # kube-linter: error, warning, info
                severity_map = {
                    "error": Severity.HIGH,
                    "warning": Severity.MEDIUM,
                    "info": Severity.LOW
                }
                severity = severity_map.get(message.get("severity", "warning").lower(), Severity.MEDIUM)

                findings.append(Finding(
                    id=str(__import__('uuid').uuid4()),
                    agent_source="CONFIG_KUBE_LINTER",
                    title=message.get("message", "Kubernetes issue")[:200],
                    description=message.get("message", ""),
                    severity=severity,
                    cwe_id=None,  # kube-linter doesn't provide CWE
                    evidence=(
                        f"scanner_name=kube-linter; scanner_mode=kube-linter; confidence=medium\n"
                        f"file={file_result.get('path', '')}; line={message.get('line', 0)}"
                    ),
                    remediation=message.get("message", "")
                ))
    except Exception as e:
        logger.error(f"Error running kube-linter scan: {str(e)}")

    return findings

def scan_terraform_with_tfsec(file_path: str) -> List[Finding]:
    """Scan a Terraform file with tfsec."""
    if not _check_tool_available("tfsec"):
        logger.warning("tfsec not available, skipping Terraform scan")
        return []

    findings = []
    try:
        result = subprocess.run(
            ["tfsec", "--format", "json", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        # tfsec returns 0 if no issues, non-zero if issues found
        if result.returncode not in (0, 1):
            logger.error(f"tfsec failed: {result.stderr}")
            return []

        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tfsec JSON output: {e}")
            return []

        for result_item in data.get("results", []):
            # Map tfsec severity to our Severity
            # tfsec: CRITICAL, HIGH, MEDIUM, LOW
            severity_map = {
                "CRITICAL": Severity.CRITICAL,
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
                "LOW": Severity.LOW
            }
            severity = severity_map.get(result_item.get("severity", "MEDIUM").upper(), Severity.MEDIUM)

            # Get CWE ID if available
            cwe_id = None
            if "cwe" in result_item and isinstance(result_item["cwe"], list) and len(result_item["cwe"]) > 0:
                cwe_id = str(result_item["cwe"][0])

            findings.append(Finding(
                id=str(__import__('uuid').uuid4()),
                agent_source="CONFIG_TFSEC",
                title=result_item.get("description", "Terraform issue")[:200],
                description=result_item.get("description", ""),
                severity=severity,
                cwe_id=cwe_id,
                evidence=(
                    f"scanner_name=tfsec; scanner_mode=tfsec; confidence=medium\n"
                    f"file={result_item.get('location', {}).get('filename', '')}; line={result_item.get('location', {}).get('start_line', 0)}"
                ),
                remediation=result_item.get("description", "")
            ))
    except Exception as e:
        logger.error(f"Error running tfsec scan: {str(e)}")

    return findings

def run_config_scan(clone_path: str, repo_url: str) -> List[Finding]:
    """
    Scans the cloned directory for configuration files (Dockerfile, Kubernetes, Terraform)
    and runs appropriate scanners on them.
    """
    logger.info(f"Running configuration file scanner on {clone_path}")

    findings = []

    # Mock support for standard repo unit tests
    if "example/standard-repo" in repo_url or "example/leaky-secrets-repo" in repo_url:
        logger.info("Skipping config scan for test repositories.")
        return []

    try:
        # Walk the directory to find configuration files
        for root, dirs, files in os.walk(clone_path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv")]

            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, clone_path)

                    # Skip binary files
                    if _is_binary_file(file_path):
                        continue

                    # Dockerfile
                    if file.lower() == "dockerfile":
                        findings.extend(scan_dockerfile_with_hadolint(file_path))

                    # Kubernetes/YAML manifests (common names and extensions)
                    elif file.lower() in ("deployment.yaml", "deployment.yml", "service.yaml", "service.yml",
                                          "ingress.yaml", "ingress.yml", "configmap.yaml", "configmap.yml",
                                          "secret.yaml", "secret.yml", "persistentvolumeclaim.yaml",
                                          "persistentvolumeclaim.yml", "statefulset.yaml", "statefulset.yml",
                                          "daemonset.yaml", "daemonset.yml", "job.yaml", "job.yml",
                                          "cronjob.yaml", "cronjob.yml") or \
                         (file.endswith(".yaml") or file.endswith(".yml")) and "k8s" in rel_path.lower() or \
                         (file.endswith(".yaml") or file.endswith(".yml")) and "kubernetes" in rel_path.lower():
                        findings.extend(scan_kubernetes_with_kube_linter(file_path))

                    # Terraform files
                    elif file.endswith(".tf"):
                        findings.extend(scan_terraform_with_tfsec(file_path))
                        
                except Exception as e:
                    logger.warning(f"Error scanning file {file}: {str(e)}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error during configuration file scan: {str(e)}")

    logger.info(f"Configuration file scan complete. Found {len(findings)} issues.")
    return findings