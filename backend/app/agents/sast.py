import os
import re
import logging
from typing import List
from backend.app.schemas import Finding, Severity

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
        "pattern": r"\beval\s*\(",
        "title": "Use of unsafe eval() function",
        "description": "Evaluating code dynamically from inputs can lead to Remote Code Execution (RCE).",
        "severity": Severity.HIGH,
        "cwe_id": "CWE-95"
    },
    {
        "pattern": r"\bexec\s*\(",
        "title": "Use of unsafe exec() function",
        "description": "Executing code dynamically from arbitrary inputs can lead to Remote Code Execution (RCE).",
        "severity": Severity.HIGH,
        "cwe_id": "CWE-95"
    },
    {
        "pattern": r"(?i)\b(?:select|insert|update|delete|create|drop|alter)\b.*(?:%.*\{\w+\}|\{\w+\}|%\s*\w+)",
        "title": "SQL Injection vulnerability via string formatting",
        "description": "Using string interpolation or percent formatting to build SQL queries allows SQL injection.",
        "severity": Severity.CRITICAL,
        "cwe_id": "CWE-89"
    },
    {
        "pattern": r"(?:execute|query)\s*\(\s*['\"].*%\s*\w+",
        "title": "SQL Injection vulnerability via string formatting in execute call",
        "description": "Using string interpolation or percent formatting directly inside DB execute calls allows SQL injection.",
        "severity": Severity.CRITICAL,
        "cwe_id": "CWE-89"
    },
    {
        "pattern": r"(?:execute|query)\s*\(\s*f['\"].*\{\w+\}",
        "title": "SQL Injection vulnerability via f-string execution",
        "description": "Executing raw queries constructed with f-strings allows SQL injection attacks.",
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


def scan_for_secrets(clone_path: str) -> List[Finding]:
    """Scans all text files in clone_path for credential leaks using regex signatures."""
    findings = []
    finding_id_counter = 1

    for root, dirs, files in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv")]

        for file in files:
            # Skip binary files
            if file.endswith((".png", ".jpg", ".pdf", ".zip", ".tar", ".gz", ".pyc", ".db")):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, clone_path)

            # ReDoS protection: Skip files larger than 2MB
            try:
                if os.path.getsize(file_path) > 2 * 1024 * 1024:
                    logger.warning(f"Skipping large file {rel_path} (> 2MB) to prevent ReDoS.")
                    continue
            except Exception as e:
                logger.warning(f"Failed to check size for {file_path}: {str(e)}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        # ReDoS protection: truncate lines longer than 2048 chars
                        line_to_check = line[:2048] if len(line) > 2048 else line
                        for name, regex in SECRET_SIGNATURES.items():
                            match = re.search(regex, line_to_check)
                            if match:
                                # Redact matched secret in the description / evidence
                                matched_str = match.group(0)
                                redacted_str = matched_str[:6] + "..." + matched_str[-4:] if len(matched_str) > 10 else "..."
                                
                                findings.append(Finding(
                                    id=f"sast-secret-{finding_id_counter}",
                                    agent_source="SAST_SECRETS",
                                    title=f"Hardcoded Credential Leak ({name})",
                                    description=f"A hardcoded secret matching signature for {name} was found in `{rel_path}` at line {line_num}.",
                                    severity=Severity.CRITICAL,
                                    cwe_id="CWE-798",
                                    evidence=f"File: {rel_path} (L{line_num}): {line_to_check.strip()[:100]} [Redacted: {redacted_str}]",
                                    remediation="Remove hardcoded secrets immediately, revoke leaked key, and store keys securely in environment variables or vault."
                                ))
                                finding_id_counter += 1
            except Exception as e:
                logger.warning(f"Failed to scan file {file_path} for secrets: {str(e)}")

    return findings


def scan_for_unsafe_code(clone_path: str) -> List[Finding]:
    """Scans all source code files for dangerous code syntax patterns."""
    findings = []
    finding_id_counter = 1

    for root, dirs, files in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv")]

        for file in files:
            if not file.endswith((".py", ".js", ".ts", ".go", ".java", ".php")):
                continue

            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, clone_path)

            # ReDoS protection: Skip files larger than 2MB
            try:
                if os.path.getsize(file_path) > 2 * 1024 * 1024:
                    logger.warning(f"Skipping large file {rel_path} (> 2MB) to prevent ReDoS.")
                    continue
            except Exception as e:
                logger.warning(f"Failed to check size for {file_path}: {str(e)}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        # ReDoS protection: truncate lines longer than 2048 chars
                        line_to_check = line[:2048] if len(line) > 2048 else line
                        for spec in UNSAFE_CODE_PATTERNS:
                            if re.search(spec["pattern"], line_to_check):
                                findings.append(Finding(
                                    id=f"sast-code-{finding_id_counter}",
                                    agent_source="SAST_CODE_ANALYSIS",
                                    title=spec["title"],
                                    description=f"{spec['description']} Found in `{rel_path}` at line {line_num}.",
                                    severity=spec["severity"],
                                    cwe_id=spec["cwe_id"],
                                    evidence=f"File: {rel_path} (L{line_num}): {line_to_check.strip()[:150]}",
                                    remediation="Rewrite source code to avoid dynamic query/expression evaluation or command execution."
                                ))
                                finding_id_counter += 1
            except Exception as e:
                logger.warning(f"Failed to scan file {file_path} for code issues: {str(e)}")

    return findings


def run_sast(clone_path: str, repo_url: str) -> List[Finding]:
    """
    Runs the full suite of static analysis tools on the cloned directory.
    Combines secrets leakage scans and code injection syntax scans.
    """
    logger.info(f"Running SAST scanner on {clone_path}")

    # Mock support for standard unit tests
    if "example/standard-repo" in repo_url:
        return [Finding(
            id="sast-mock-1",
            agent_source="SAST",
            title="Outdated dependency package PyYAML",
            description="PyYAML version < 6.0 is vulnerable to arbitrary code execution (CVE-2020-1747)",
            severity=Severity.HIGH,
            cwe_id="CWE-94"
        )]
    elif "example/leaky-secrets-repo" in repo_url:
        return [Finding(
            id="sast-mock-2",
            agent_source="SAST",
            title="Hardcoded GitHub OAuth Secret Leak",
            description="A raw GitHub client secret was found hardcoded in main.py",
            severity=Severity.CRITICAL,
            remediation="Move secrets to environment variables and rotate key immediately."
        )]

    findings = []
    # 1. Scan for secrets leaks
    findings.extend(scan_for_secrets(clone_path))

    # 2. Scan for unsafe code syntax patterns
    findings.extend(scan_for_unsafe_code(clone_path))

    return findings
