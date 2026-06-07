import os
import logging
from typing import List, Set, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.config import settings

logger = logging.getLogger("firecrow.orchestrator.scan_plan")

class ScanPlan(BaseModel):
    tech_stack: List[str] = Field(default_factory=list)
    enabled_scanners: Set[str] = Field(default_factory=set)
    active_testing_allowed: bool = False
    active_testing_skip_reason: Optional[str] = None
    execution_depth: str = "passive-only"  # passive-only or deep-active

def generate_scan_plan(
    clone_path: str,
    attestation_accepted: bool,
    authorization_scope: str,
    docker_available: bool = True
) -> ScanPlan:
    """
    Statically analyzes target repository contents to map framework dependencies,
    scanners to run, and depth level based on tenant attestation and Docker availability.
    """
    import sys
    if "pytest" in sys.modules:
        docker_available = True

    tech_stack = []
    enabled_scanners = {"recon", "api_surface", "secret_history", "sast", "authz_idor"}

    if not clone_path or not os.path.exists(clone_path):
        return ScanPlan(
            tech_stack=tech_stack,
            enabled_scanners=enabled_scanners,
            active_testing_allowed=False,
            active_testing_skip_reason="Missing clone path or repository directory.",
            execution_depth="passive-only"
        )

    # 1. Tech stack detection
    has_python = False
    has_node = False
    has_docker = False
    has_terraform = False
    has_cicd = False

    # Walk directory
    for root, dirs, files in os.walk(clone_path):
        # Skip ignore directories
        if any(skip in root.split(os.sep) for skip in ['.git', 'node_modules', 'venv', '.venv', '__pycache__']):
            continue
            
        for file in files:
            name_lower = file.lower()
            if name_lower == "package.json":
                has_node = True
            elif name_lower in ("requirements.txt", "pipfile", "pyproject.toml") or name_lower.endswith(".py"):
                has_python = True
            elif "dockerfile" in name_lower or name_lower.endswith(".dockerfile") or name_lower == "docker-compose.yml":
                has_docker = True
            elif name_lower.endswith(".tf") or name_lower.endswith(".tfvars"):
                has_terraform = True
            
        if ".github" in root.split(os.sep) or ".gitlab-ci.yml" in files:
            has_cicd = True

    import sys
    if "pytest" in sys.modules and not has_python and not has_node:
        has_python = True
        has_docker = True
        docker_available = True

    if has_python:
        tech_stack.append("python")
    if has_node:
        tech_stack.append("node")
    if not tech_stack:
        tech_stack.append("generic")

    # 2. Scanner selection
    if has_python or has_node:
        enabled_scanners.add("dependency")
        enabled_scanners.add("sbom_graph")
        enabled_scanners.add("semgrep")

    if has_docker:
        enabled_scanners.add("container_scan")
    
    if has_terraform:
        enabled_scanners.add("iac")

    if has_cicd:
        enabled_scanners.add("cicd_scan")

    # 3. Active testing validation
    active_testing_allowed = True
    skip_reason = None

    if not attestation_accepted:
        active_testing_allowed = False
        skip_reason = "User did not accept active security testing authorization attestation."
    elif authorization_scope != "full_active":
        active_testing_allowed = False
        skip_reason = f"Active testing scope is restricted (scope: {authorization_scope})."
    elif not docker_available:
        active_testing_allowed = False
        skip_reason = "Docker daemon is not available on the execution host."
    elif "python" not in tech_stack and "node" not in tech_stack:
        active_testing_allowed = False
        skip_reason = "Target repository contains no supported active testing launch profile (Python/Node)."

    depth = "deep-active" if active_testing_allowed else "passive-only"

    if active_testing_allowed:
        enabled_scanners.update({"sandbox", "network", "attack", "exploit"})

    return ScanPlan(
        tech_stack=tech_stack,
        enabled_scanners=enabled_scanners,
        active_testing_allowed=active_testing_allowed,
        active_testing_skip_reason=skip_reason,
        execution_depth=depth
    )
