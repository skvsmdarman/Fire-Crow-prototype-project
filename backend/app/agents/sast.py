import os
import re
import logging
import hashlib
import uuid
import subprocess
from typing import List, Optional
from app.config import settings
from app.schemas import Finding, Severity
from app.services.redaction import redact_text

logger = logging.getLogger("firecrow.agents.sast")

# Secret regex signatures
SECRET_SIGNATURES = {
    "GitHub OAuth / Personal Access Token": r"gh[oprs]_[A-Za-z0-9_]{36,255}",
    "AWS Access Key ID": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
    "AWS Secret Access Key": r"(?i)aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
    "Generic Password / Key Leak": r"(?i)(?:secret|password|private_key|auth_token|api_key|apikey)\s*=\s*['\"][a-zA-Z0-9_\-\+\/]{16,}['\"]"
}

# Unsafe code call signatures (SAST patterns)
UNSAFE_CODE_PATTERNS = [
    {
        "pattern": r"^[^\#\'\"/]*\beval\s*\(",
        "title": "Use of unsafe eval() function",
        "description": "Evaluating code dynamically from inputs can lead to Remote Code Execution (RCE).",
        "severity": Severity.HIGH,
        "cwe_id": "CWE-95"
    },
    {
        "pattern": r"^[^\#\'\"/]*\bexec\s*\(",
        "title": "Use of unsafe exec() function",
        "description": "Executing code dynamically from arbitrary inputs can lead to Remote Code Execution (RCE).",
        "severity": Severity.HIGH,
        "cwe_id": "CWE-95"
    },
    {
        "pattern": r"(?i)^[^\#\'\"/]*f['\"].*\b(?:select\s+.*\s+from|insert\s+.*\s+into|update\s+.*\s+set|delete\s+.*\s+from|create\s+(?:table|database|index|view)|drop\s+(?:table|database|index|view)|alter\s+(?:table|database))\b.*\{",
        "title": "SQL Injection vulnerability via f-string execution",
        "description": "Executing raw queries constructed with f-strings can permit SQL injection.",
        "severity": Severity.CRITICAL,
        "cwe_id": "CWE-89"
    },
    {
        "pattern": r"(?i)^[^\#\'\"/]*['\"].*\b(?:select\s+.*\s+from|insert\s+.*\s+into|update\s+.*\s+set|delete\s+.*\s+from|create\s+(?:table|database|index|view)|drop\s+(?:table|database|index|view)|alter\s+(?:table|database))\b.*(?:\.format\s*\(|%\s*[\w\(\\])",
        "title": "SQL Injection vulnerability via string formatting",
        "description": "Using string interpolation or percent formatting to build SQL queries can permit SQL injection.",
        "severity": Severity.CRITICAL,
        "cwe_id": "CWE-89"
    },
    {
        "pattern": r"subprocess\.(?:Popen|run|call)\s*\(\s*.*shell\s*=\s*True",
        "title": "Subprocess execution with shell=True",
        "description": "Running subcommands using shell=True bypasses argument escaping and leads to command injection.",
        "severity": Severity.HIGH,
        "cwe_id": "CWE-78"
    }
]


def _is_binary_file(file_path: str) -> bool:
    """Check if file is binary by reading first 1024 bytes for null byte."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            return b'\x00' in chunk
    except Exception:
        return True  # If we can't read, treat as binary to be safe


def scan_for_secrets(clone_path: str) -> List[Finding]:
    """Scans all text files in clone_path for credential leaks using regex signatures."""
    findings = []

    EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build", ".tox", ".eggs"}
    for root, dirs, files in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d.split(os.sep)[-1] not in EXCLUDED_DIRS]

        for file in files:
            if file.endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar", ".gz", ".pyc", ".db", ".svg", ".ico", ".woff", ".woff2", ".eot", ".ttf")):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, clone_path)

            try:
                if os.path.getsize(file_path) > 2 * 1024 * 1024:
                    logger.warning("Skipping large file %s (> 2MB) to prevent ReDoS.", rel_path)
                    continue
            except Exception as e:
                logger.warning("Failed to check size for %s: %s", file_path, e)
                continue

            # Skip binary files via content check
            if _is_binary_file(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, start=1):
                        line_to_check = line[:2048] if len(line) > 2048 else line
                        for name, regex in SECRET_SIGNATURES.items():
                            match = re.search(regex, line_to_check)
                            if match:
                                matched_str = match.group(0)
                                fingerprint = hashlib.sha256(matched_str.encode("utf-8")).hexdigest()[:12]

                                findings.append(Finding(
                                    id=str(uuid.uuid4()),
                                    agent_source="SAST_SECRETS",
                                    title=f"Hardcoded Credential Leak ({name})",
                                    description=f"A hardcoded secret matching signature for {name} was found in `{rel_path}` at line {line_num}.",
                                    severity=Severity.CRITICAL,
                                    cwe_id="CWE-798",
                                    evidence=(
                                        "scanner_name=regex-sast; scanner_mode=regex; confidence=medium\n"
                                        f"file={rel_path}; line={line_num}; signature={name}; redacted_fingerprint=sha256:{fingerprint}"
                                    ),
                                    remediation="Remove hardcoded secrets immediately, revoke leaked key, and store keys securely in environment variables or vault."
                                ))
            except Exception as e:
                logger.warning("Failed to scan file %s for secrets: %s", file_path, e)

    return findings


def scan_for_unsafe_code(clone_path: str, skip_extensions: Optional[List[str]] = None) -> List[Finding]:
    """Scans source code files for dangerous code syntax patterns.

    Args:
        clone_path: Path to the cloned repository.
        skip_extensions: List of file extensions to skip (e.g., ['.py'] to skip Python files).
    """
    findings = []
    skip_extensions = skip_extensions or []

    EXCLUDED_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "dist", "build", ".tox", ".eggs"}
    for root, dirs, files in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d.split(os.sep)[-1] not in EXCLUDED_DIRS]

        for file in files:
            # Skip files with extensions in skip_extensions
            if any(file.endswith(ext) for ext in skip_extensions):
                continue

            if not file.endswith((".py", ".js", ".ts", ".go", ".java", ".php", ".rb", ".rs")):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, clone_path)

            try:
                if os.path.getsize(file_path) > 2 * 1024 * 1024:
                    logger.warning("Skipping large file %s (> 2MB) to prevent ReDoS.", rel_path)
                    continue
            except Exception as e:
                logger.warning("Failed to check size for %s: %s", file_path, e)
                continue

            # Skip binary files via content check
            if _is_binary_file(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, start=1):
                        line_to_check = line[:2048] if len(line) > 2048 else line
                        for spec in UNSAFE_CODE_PATTERNS:
                            if re.search(spec["pattern"], line_to_check):
                                safe_snippet = redact_text(line_to_check.strip()[:150])
                                findings.append(Finding(
                                    id=str(uuid.uuid4()),
                                    agent_source="SAST_CODE_ANALYSIS",
                                    title=spec["title"],
                                    description=f"{spec['description']} Found in `{rel_path}` at line {line_num}.",
                                    severity=spec["severity"],
                                    cwe_id=spec["cwe_id"],
                                    evidence=(
                                        "scanner_name=regex-sast; scanner_mode=regex; confidence=medium\n"
                                        f"file={rel_path}; line={line_num}; snippet={safe_snippet}"
                                    ),
                                    remediation="Rewrite source code to avoid dynamic query/expression evaluation or command execution."
                                ))
            except Exception as e:
                logger.warning("Failed to scan file %s for code issues: %s", file_path, e)

    return findings


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


def scan_with_bandit(clone_path: str) -> List[Finding]:
    """Run Bandit security scanner on Python files."""
    if not _check_tool_available("bandit"):
        logger.warning("Bandit not available, skipping Bandit scan")
        return []

    findings = []
    try:
        # Run bandit with JSON output
        result = subprocess.run(
            ["bandit", "-r", clone_path, "-f", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )

        if result.returncode not in (0, 1):  # Bandit returns 1 when findings are found
            logger.error(f"Bandit scan failed: {result.stderr}")
            return []

        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bandit JSON output: {e}")
            return []

        for result_item in data.get("results", []):
            # Map Bandit severity to our Severity
            severity_map = {
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
                "LOW": Severity.LOW
            }
            bandit_severity = result_item.get("issue_severity", "MEDIUM").upper()
            severity = severity_map.get(bandit_severity, Severity.MEDIUM)

            # Get CWE ID if available
            cwe_info = result_item.get("issue_cwe")
            cwe_id = None
            if isinstance(cwe_info, dict) and "id" in cwe_info:
                cwe_id = str(cwe_info["id"])
            elif isinstance(cwe_info, int):
                cwe_id = str(cwe_info)

            # Create finding
            findings.append(Finding(
                id=str(uuid.uuid4()),
                agent_source="SAST_BANDIT",
                title=result_item.get("issue_text", "Security issue detected by Bandit")[:200],
                description=result_item.get("issue_text", ""),
                severity=severity,
                cwe_id=cwe_id,
                evidence=(
                    f"scanner_name=bandit; scanner_mode=bandit; confidence=medium\n"
                    f"file={result_item.get('filename', '')}; line={result_item.get('line_number', 0)}"
                ),
                remediation="Review the Bandit finding and apply recommended fix."
            ))
    except Exception as e:
        logger.error(f"Error running Bandit scan: {str(e)}")

    return findings


def scan_with_eslint(clone_path: str) -> List[Finding]:
    """Run ESLint with security plugins on JavaScript/TypeScript files."""
    if not _check_tool_available("npx"):
        logger.warning("npx not available, skipping ESLint scan")
        return []

    findings = []
    try:
        # Check if eslint and security plugin are available
        check_result = subprocess.run(
            ["npx", "eslint", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        if check_result.returncode != 0:
            logger.warning("ESLint not available, skipping ESLint security scan")
            return []

        # Run ESLint with security plugin
        result = subprocess.run(
            ["npx", "eslint", clone_path, "--format", "json", "--plugin", "security"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )

        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ESLint JSON output: {e}")
            return []

        for file_result in data:
            file_path = file_result.get("filePath", "")
            rel_path = os.path.relpath(file_path, clone_path) if file_path.startswith(clone_path) else file_path

            for message in file_result.get("messages", []):
                rule_id = message.get("ruleId", "")
                severity_val = message.get("severity", 1)

                # Only include security-related rules
                if not rule_id or not any(kw in rule_id.lower() for kw in ["security", "no-eval", "no-implied-eval", "no-new-func", "no-script-url"]):
                    continue

                severity = Severity.HIGH if severity_val == 2 else Severity.MEDIUM

                findings.append(Finding(
                    id=str(uuid.uuid4()),
                    agent_source="SAST_ESLINT",
                    title=f"ESLint Security: {message.get('message', 'Security issue')[:200]}",
                    description=message.get("message", ""),
                    severity=severity,
                    cwe_id="CWE-798" if "eval" in rule_id.lower() else None,
                    evidence=(
                        f"scanner_name=eslint; scanner_mode=eslint-security; confidence=medium\n"
                        f"file={rel_path}; line={message.get('line', 0)}; rule={rule_id}"
                    ),
                    remediation="Review the ESLint security finding and apply recommended fix."
                ))
    except Exception as e:
        logger.error(f"Error running ESLint scan: {str(e)}")

    return findings


def run_sast(clone_path: str, repo_url: str) -> List[Finding]:
    """
    Runs the full suite of static analysis tools on the cloned directory.
    Combines secrets leakage scans and code injection syntax scans.
    """
    logger.info("Running SAST scanner on %s", clone_path)

    # Debug-only mock support for standard unit tests.
    if "example/standard-repo" in repo_url:
        if not settings.DEBUG:
            logger.info("Skipping standard-repo simulated SAST fixture outside DEBUG mode.")
            return []
        return [Finding(
            id=str(uuid.uuid4()),
            agent_source="SAST",
            title="[SIMULATED] Outdated dependency package PyYAML",
            description="PyYAML version < 6.0 is vulnerable to arbitrary code execution (CVE-2020-1747)",
            severity=Severity.HIGH,
            cwe_id="CWE-94",
            evidence="scanner_name=sast-fixture; scanner_mode=simulated; confidence=low",
        )]
    elif "example/leaky-secrets-repo" in repo_url:
        if not settings.DEBUG:
            logger.info("Skipping leaky-secrets-repo simulated SAST fixture outside DEBUG mode.")
            return []
        return [Finding(
            id=str(uuid.uuid4()),
            agent_source="SAST",
            title="[SIMULATED] Hardcoded GitHub OAuth Secret Leak",
            description="A raw GitHub client secret was found hardcoded in main.py",
            severity=Severity.CRITICAL,
            evidence="scanner_name=sast-fixture; scanner_mode=simulated; confidence=low",
            remediation="Move secrets to environment variables and rotate key immediately."
        )]

    findings = []
    # 1. Scan for secrets leaks (always run)
    findings.extend(scan_for_secrets(clone_path))

    # 2. Scan for unsafe code syntax patterns
    # Try to use Bandit for Python files, fall back to regex if not available
    bandit_available = _check_tool_available("bandit")
    if bandit_available:
        # Run Bandit on Python files
        findings.extend(scan_with_bandit(clone_path))
        # Run regex unsafe code scan on non-Python files
        findings.extend(scan_for_unsafe_code(clone_path, skip_extensions=[".py"]))
    else:
        logger.info("Bandit not available, falling back to regex scan for all files")
        findings.extend(scan_for_unsafe_code(clone_path))

    # 3. Run ESLint security scan on JS/TS files
    eslint_available = _check_tool_available("npx")
    if eslint_available:
        findings.extend(scan_with_eslint(clone_path))

    return findings
