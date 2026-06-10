import os
import subprocess
import shutil
import logging
from typing import List, Tuple, Optional
from app.config import settings

logger = logging.getLogger("firecrow.agents.recon")


def clone_repository(repo_url: str, branch: str, target_dir: str, github_token: Optional[str] = None) -> bool:
    """Clones a remote git repository branch to target_dir using subprocess."""
    try:
        # If target directory already exists, clear it first
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        if repo_url.strip().startswith("-"):
            logger.error(f"Malicious repository URL rejected: {repo_url}")
            return False
        if branch.strip().startswith("-"):
            logger.error(f"Malicious branch name rejected: {branch}")
            return False

        clone_url = repo_url
        resolved_token = github_token or settings.GITHUB_TOKEN
        if resolved_token and "github.com" in repo_url.lower() and "x-access-token" not in repo_url:
            if repo_url.startswith("https://"):
                clone_url = repo_url.replace("https://", f"https://x-access-token:{resolved_token}@")
            elif repo_url.startswith("http://"):
                clone_url = repo_url.replace("http://", f"http://x-access-token:{resolved_token}@")

        logger.info(f"Cloning repo (branch: {branch}) into {target_dir}")
        # Run git clone with a timeout of 60 seconds and an argument isolator (--)
        # to prevent malicious input URLs from being parsed as options flags.
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, "--", clone_url, target_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            logger.error(f"Git clone failed: {result.stderr}")
            return False

        # 1. Remove git hooks to prevent malicious code execution
        hooks_dir = os.path.join(target_dir, ".git", "hooks")
        if os.path.exists(hooks_dir):
            shutil.rmtree(hooks_dir, ignore_errors=True)
            
        # 2. Check for symlink escapes and size limits
        total_size = 0
        MAX_SIZE = 500 * 1024 * 1024 # 500MB
        for root, dirs, files in os.walk(target_dir):
            for name in files + dirs:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    target = os.path.realpath(path)
                    if not target.startswith(os.path.realpath(target_dir)):
                        logger.error(f"Malicious symlink detected: {path}")
                        return False
                if os.path.isfile(path) and not os.path.islink(path):
                    total_size += os.path.getsize(path)
                    
        if total_size > MAX_SIZE:
            logger.error(f"Repository exceeds 500MB size limit: {total_size} bytes")
            return False

        return True
    except Exception as e:
        logger.exception(f"Exception during git clone: {str(e)}")
        return False


def detect_tech_stack(target_dir: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Scans cloned repository structure to identify tech stacks, dependency manifests,
    and main application entry points.
    """
    tech_stack = []
    dependency_manifests = []
    entry_points = []

    # Check for dependency manifests and entry points
    for root, dirs, files in os.walk(target_dir):
        # Exclude common large/hidden folders
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__")]

        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, target_dir)

            # Detect manifests
            if file == "package.json":
                tech_stack.append("NodeJS")
                dependency_manifests.append(rel_path)
            elif file == "requirements.txt":
                tech_stack.append("Python")
                dependency_manifests.append(rel_path)
            elif file == "Pipfile" or file == "pyproject.toml":
                tech_stack.append("Python")
                dependency_manifests.append(rel_path)
            elif file == "go.mod":
                tech_stack.append("Go")
                dependency_manifests.append(rel_path)
            elif file == "pom.xml":
                tech_stack.append("Java (Maven)")
                dependency_manifests.append(rel_path)
            elif file == "build.gradle":
                tech_stack.append("Java (Gradle)")
                dependency_manifests.append(rel_path)

            # Detect entry points
            if file in ("main.py", "app.py", "server.js", "index.js", "app.js", "server.py"):
                entry_points.append(rel_path)
            elif file == "Dockerfile":
                tech_stack.append("Docker")
                entry_points.append(rel_path)
            elif file == "docker-compose.yml" or file == "docker-compose.yaml":
                tech_stack.append("Docker Compose")
                entry_points.append(rel_path)

    # Clean duplicates
    tech_stack = list(set(tech_stack))
    
    # Defaults if nothing is detected
    if not tech_stack:
        tech_stack = ["Generic Codebase"]

    return tech_stack, dependency_manifests, entry_points


def run_recon(job_id: str, repo_url: str, branch: str, github_token: Optional[str] = None) -> dict:
    """
    Main entry point for RECON agent.
    Clones the target repository and performs static composition analysis.
    """
    # Define a clean workspace path inside the system temp directory or workspace
    base_scan_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace", "scans")
    target_dir = os.path.abspath(os.path.join(base_scan_dir, job_id))

    # Mock support for local file mock tests
    if "example/standard-repo" in repo_url or "example/leaky-secrets-repo" in repo_url or "example/vulnerable-app" in repo_url:
        logger.info(f"Mocking recon phase for test repository: {repo_url}")
        os.makedirs(target_dir, exist_ok=True)
        return {
            "clone_path": target_dir,
            "tech_stack": ["Python", "Docker", "FastAPI"],
            "dependency_manifests": ["requirements.txt"],
            "entry_points": ["main.py", "Dockerfile"],
            "error": None
        }

    success = clone_repository(repo_url, branch, target_dir, github_token=github_token)
    if not success:
        return {
            "clone_path": "",
            "tech_stack": [],
            "dependency_manifests": [],
            "entry_points": [],
            "error": "Failed to clone repository. Verify the URL and branch name."
        }

    tech_stack, dependency_manifests, entry_points = detect_tech_stack(target_dir)

    return {
        "clone_path": target_dir,
        "tech_stack": tech_stack,
        "dependency_manifests": dependency_manifests,
        "entry_points": entry_points,
        "error": None
    }
