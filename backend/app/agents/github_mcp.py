import logging
import re
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from app.config import settings
from app.schemas import Finding, Severity
from app.services.safe_llm import is_llm_enabled, safe_llm_call

logger = logging.getLogger("firecrow.agents.github_mcp")

# Standard labels for Fire Crow security audit issues
SECURITY_LABELS = {
    "firecrow": "Automated security audit by Fire Crow",
    "critical": "Critical severity finding",
    "high": "High severity finding",
    "medium": "Medium severity finding",
    "low": "Low severity finding",
    "info": "Informational finding",
    "security": "Security-related issue",
    "needs-triage": "Requires manual review",
}


def _build_issue_labels(findings: List[Finding]) -> List[str]:
    """Build a list of GitHub labels based on findings severity."""
    labels = ["firecrow", "security"]
    has_critical = any(f.severity == Severity.CRITICAL for f in findings)
    has_high = any(f.severity == Severity.HIGH for f in findings)
    has_medium = any(f.severity == Severity.MEDIUM for f in findings)
    has_low = any(f.severity == Severity.LOW for f in findings)

    if has_critical:
        labels.append("critical")
    if has_high:
        labels.append("high")
    if has_medium:
        labels.append("medium")
    if has_low:
        labels.append("low")
    if not has_critical and not has_high:
        labels.append("needs-triage")

    return labels


def _ensure_labels_exist(owner: str, repo: str, token: str, labels: List[str]) -> None:
    """Create labels in the repository if they don't already exist."""
    existing_url = f"https://api.github.com/repos/{owner}/{repo}/labels?per_page=100"
    existing_data, status, _ = _github_api_request(existing_url, "GET", token)
    existing_names = set()
    if existing_data and isinstance(existing_data, list):
        existing_names = {lbl.get("name", "") for lbl in existing_data}

    for label_name in labels:
        if label_name in existing_names:
            continue
        label_desc = SECURITY_LABELS.get(label_name, f"Fire Crow: {label_name}")
        # Color based on label type
        color_map = {
            "firecrow": "f97316",  # orange
            "security": "e11d48",  # rose
            "critical": "dc2626",  # red
            "high": "ea580c",      # orange
            "medium": "ca8a04",    # yellow
            "low": "2563eb",       # blue
            "info": "6b7280",      # gray
            "needs-triage": "9333ea",  # purple
        }
        color = color_map.get(label_name, "6b7280")
        create_url = f"https://api.github.com/repos/{owner}/{repo}/labels"
        _github_api_request(create_url, "POST", token, {"name": label_name, "description": label_desc, "color": color})


def _github_api_request(url: str, method: str, token: str, payload: dict | None = None) -> Tuple[Any, int, str]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "Fire-Crow-Security-Scanner")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")), response.status, ""
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8") if err.fp else ""
        return None, err.code, err_body
    except Exception as exc:
        return None, 500, str(exc)


def _escape_markdown_text(value: str | None) -> str:
    """Escape Markdown control characters while preserving readable line breaks."""
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|>])", r"\\\1", text)


def _code_block(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    longest_backtick_run = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest_backtick_run + 1)
    return f"{fence}\n{text}\n{fence}"

def parse_repo_url(url: str) -> tuple[str, str] | None:
    """Parses owner and repository name from a GitHub URL."""
    # Handles https://github.com/owner/repo, git@github.com:owner/repo, etc.
    pattern = r"(?:github\.com[:/])([^/]+)/([^/.]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None

def _get_smart_finding_details(finding: Finding) -> Dict[str, str]:
    """Uses LLM to enrich findings with non-technical assessment and step-by-step fixes for GitHub reports."""
    details = {
        "non_technical_summary": f"This security issue is a {finding.severity.value} vulnerability which may expose sensitive application assets or logic. It was identified by {finding.agent_source} tools.",
        "impact": "Exploitation of this vulnerability may compromise the integrity, availability, or confidentiality of the application, leading to unauthorized access, system degradation, or data disclosure.",
        "remediation_steps": finding.remediation or "Follow secure coding practices, enforce strict parameter validation, sanitize all inputs, and use encrypted configuration parameters."
    }

    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        return details

    prompt = f"""You are a senior security researcher. Explain the following vulnerability so that even a non-technical manager (or junior developer) can understand:
Title: {finding.title}
Severity: {finding.severity.value}
Description: {finding.description}
CWE: {finding.cwe_id or 'N/A'}
Evidence: {finding.evidence or 'None'}

Provide your response in JSON format. Do not use markdown code block wrappers (like ```json). Respond with a raw JSON object containing these keys:
- "non_technical_summary": A clear explanation of what this vulnerability means in plain English, why it is dangerous, and what the real-world business risk is.
- "impact": The technical impact of this vulnerability on the systems and data.
- "remediation_steps": Actionable, step-by-step coding instructions to fix the issue.
"""
    try:
        res = safe_llm_call(prompt, max_tokens=1000, temperature=0.2)
        if res:
            res_clean = res.strip()
            if res_clean.startswith("```json"):
                res_clean = res_clean.removeprefix("```json").removesuffix("```").strip()
            elif res_clean.startswith("```"):
                res_clean = res_clean.removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(res_clean)
            if "non_technical_summary" in parsed and "impact" in parsed and "remediation_steps" in parsed:
                return {
                    "non_technical_summary": parsed["non_technical_summary"],
                    "impact": parsed["impact"],
                    "remediation_steps": parsed["remediation_steps"]
                }
    except Exception as e:
        logger.warning(f"Failed to generate smart details for finding {finding.title}: {e}")
    
    return details


def format_findings_markdown(repo_url: str, findings: List[Finding]) -> str:
    """Formats the security audit findings into a premium markdown report."""
    if not findings:
        return "## Fire Crow Security Audit\n\nNo security vulnerabilities were identified in this audit."

    total_findings = len(findings)
    by_severity = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 0,
        Severity.MEDIUM: 0,
        Severity.LOW: 0,
        Severity.INFO: 0,
    }
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    body = "# Fire Crow Security Audit Report\n\n"
    body += f"An autonomous security audit has completed for **{_escape_markdown_text(repo_url)}**.\n\n"
    body += "### Summary of Findings\n"
    body += f"- **Total Vulnerabilities**: {total_findings}\n"
    body += f"- **Critical**: {by_severity[Severity.CRITICAL]}\n"
    body += f"- **High**: {by_severity[Severity.HIGH]}\n"
    body += f"- **Medium**: {by_severity[Severity.MEDIUM]}\n"
    body += f"- **Low**: {by_severity[Severity.LOW]}\n\n"
    
    body += "### Vulnerability Details\n"
    for idx, finding in enumerate(findings, 1):
        severity_label = finding.severity.value.upper()
        
        # Call smart helper
        smart_details = _get_smart_finding_details(finding)
        
        body += f"#### {idx}. {_escape_markdown_text(finding.title)} ({severity_label})\n"
        body += f"- **Source**: {_escape_markdown_text(finding.agent_source)}\n"
        if finding.cwe_id:
            body += f"- **CWE**: {_escape_markdown_text(finding.cwe_id)}\n"
        body += f"- **Technical Description**: {_escape_markdown_text(finding.description)}\n"
        body += f"- **Plain English Summary (For Non-Technical Users)**: {smart_details['non_technical_summary']}\n"
        body += f"- **Security & Business Impact**: {smart_details['impact']}\n"
        if finding.evidence:
            body += f"- **Evidence/Proof**:\n\n{_code_block(finding.evidence)}\n"
        body += f"- **Actionable Remediation Guide**: {smart_details['remediation_steps']}\n"
        body += "\n---\n"

    body += "\n\n*Report generated automatically by Fire Crow Orchestration Engine.*"
    return body


def _build_ai_pr_summary(remediations: List[Dict[str, Any]], findings: List[Finding]) -> str | None:
    if not remediations or not is_llm_enabled("pr_description"):
        return None

    rem_titles: List[str] = []
    for rem in remediations[:3]:
        title = rem.get("title")
        if not title and rem.get("finding_id"):
            title = next((finding.title for finding in findings if finding.id == rem["finding_id"]), None)
        if title:
            rem_titles.append(str(title))

    if not rem_titles:
        return None

    prompt = (
        "Summarize these security fixes in one sentence for a pull request description:\n"
        + "\n".join(f"- {title}" for title in rem_titles)
    )
    summary = safe_llm_call(prompt, max_tokens=40, temperature=0.2)
    if not summary:
        return None
    return summary.strip()

class GitMCPClient:
    """A lightweight HTTP/SSE client implementation for GitMCP."""
    owner: str
    repo: str
    token: str
    sse_url: str
    write_url: str | None

    def __init__(self, owner: str, repo: str, token: str = ""):
        self.owner = owner
        self.repo = repo
        self.token = token
        # The base SSE endpoint URL for this specific repository
        self.sse_url = f"https://gitmcp.io/{owner}/{repo}"
        self.write_url = None
        self.last_connect_status: int | None = None
        self.last_connect_error = ""

    def connect_sse(self) -> bool:
        """Connects to the SSE stream to discover the messaging endpoint."""
        logger.info("Connecting to GitMCP SSE endpoint: %s", self.sse_url)
        self.last_connect_status = None
        self.last_connect_error = ""
        try:
            req = urllib.request.Request(self.sse_url)
            req.add_header("Accept", "text/event-stream")
            if self.token:
                req.add_header("Authorization", f"token {self.token}")

            # Read the first chunk of the stream to find the connect endpoint
            with urllib.request.urlopen(req, timeout=10) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("event: connect"):
                        # Next line should be data
                        continue
                    if line_str.startswith("data:"):
                        data_content = line_str[5:].strip()
                        data = json.loads(data_content)
                        # Extract messaging/write URL
                        endpoint = data.get("uri") or data.get("endpoint")
                        if endpoint:
                            if endpoint.startswith("/"):
                                self.write_url = f"https://gitmcp.io{endpoint}"
                            else:
                                self.write_url = endpoint
                            logger.info("Discovered GitMCP write endpoint: %s", self.write_url)
                            return True
        except urllib.error.HTTPError as exc:
            self.last_connect_status = exc.code
            self.last_connect_error = str(exc)
            if exc.code in {401, 403}:
                logger.info(
                    "GitMCP SSE access denied for %s/%s (HTTP %s). Direct GitHub fallback will be used when available.",
                    self.owner,
                    self.repo,
                    exc.code,
                )
            else:
                logger.warning(
                    "GitMCP SSE connection returned HTTP %s for %s/%s.",
                    exc.code,
                    self.owner,
                    self.repo,
                )
        except Exception as exc:
            self.last_connect_error = str(exc)
            logger.warning("GitMCP SSE connection failed for %s/%s: %s", self.owner, self.repo, exc)
        return False

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any] | None:
        """Invokes an MCP tool on the connected server."""
        if not self.write_url:
            if not self.connect_sse() or not self.write_url:
                logger.error("Failed to obtain GitMCP write URL for %s/%s", self.owner, self.repo)
                return None

        # self.write_url is guaranteed to be a non-None string here
        write_url: str = self.write_url

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(write_url, data=data)
            req.add_header("Content-Type", "application/json")
            if self.token:
                req.add_header("Authorization", f"token {self.token}")
                
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if "error" in res_data:
                    logger.error("MCP tool call returned error: %s", res_data.get("error"))
                    return None
                return res_data.get("result")
        except Exception as exc:
            logger.error("Failed to invoke GitMCP tool %s: %s", tool_name, exc)
        return None

def run_github_mcp(
    job_id: str,
    repo_url: str,
    findings: List[Finding],
    remediations: List[Dict[str, Any]] | None = None,
    github_token: str | None = None,
) -> Dict[str, Any]:
    """
    Main entry point for GITHUB_MCP agent.
    Connects to the repository's gitmcp.io remote server to raise issues/PRs.
    Falls back to direct GitHub API if gitmcp.io is unreachable or unauthenticated.
    """
    # 1. Parse repository details
    repo_info = parse_repo_url(repo_url)
    if not repo_info:
        logger.warning("Unsupported git URL for GitHub integration: %s", repo_url)
        return {
            "github_issue_created": False,
            "github_pr_created": False,
            "github_mcp_logs": ["Unsupported repository URL format."]
        }

    owner, repo = repo_info
    logs = [f"Initiated GitHub MCP agent for {owner}/{repo}"]

    # 2. Check mock/debug
    resolved_token = github_token or settings.GITHUB_TOKEN
    is_mock = "example/" in repo_url or settings.DEBUG and not resolved_token
    if is_mock:
        logs.append("Running in development/mock mode. Simulating GitHub Issue creation and PR creation.")
        logs.append(f"Simulated creation of security issue on repository {owner}/{repo}.")
        pr_created = False
        pr_url = ""
        branch = ""
        if remediations:
            logs.append(f"Simulated creation of PR with {len(remediations)} remediation(s).")
            pr_created = True
            pr_url = f"https://github.com/{owner}/{repo}/pull/99"
            branch = f"security-fix-fc-{job_id[:8]}"
            
        return {
            "github_issue_created": True,
            "github_pr_created": pr_created,
            "github_pr_url": pr_url,
            "github_branch": branch,
            "github_mcp_logs": logs
        }

    # 3. Format findings and build labels
    issue_title = "Fire Crow Security Scan Report"
    issue_body = format_findings_markdown(repo_url, findings)
    issue_labels = _build_issue_labels(findings)

    # 4. Ensure labels exist in the repository
    if resolved_token:
        logs.append(f"Ensuring security labels exist in {owner}/{repo}...")
        _ensure_labels_exist(owner, repo, resolved_token, issue_labels)

    # 5. Attempt GitMCP connection
    token = resolved_token
    client = GitMCPClient(owner=owner, repo=repo, token=token)
    
    logs.append(f"Attempting to connect to gitmcp.io remote server for {owner}/{repo}...")
    success = False
    
    # Try calling gitmcp create_issue tool
    if client.connect_sse():
        logs.append("Connected to GitMCP server. Invoking 'create_issue' tool...")
        result = client.call_tool("create_issue", {
            "owner": owner,
            "repo": repo,
            "title": issue_title,
            "body": issue_body,
            "labels": issue_labels
        })
        if result:
            success = True
            logs.append(f"Successfully raised issue via GitMCP: {result.get('url', 'Created')}")
        else:
            logs.append("GitMCP 'create_issue' tool call failed.")
    elif client.last_connect_status in {401, 403}:
        logs.append("GitMCP access was denied for this repository. Using direct GitHub REST API fallback.")
    else:
        logs.append("GitMCP was unavailable. Using direct GitHub REST API fallback.")

    # 6. Fallback to GitHub REST API directly
    if not success:
        if not token:
            logs.append("No GITHUB_TOKEN configured. Cannot complete API write operations.")
            return {
                "github_issue_created": False,
                "github_pr_created": False,
                "github_mcp_logs": logs
            }
            
        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            data = json.dumps({
                "title": issue_title,
                "body": issue_body,
                "labels": issue_labels
            }).encode("utf-8")
            
            req = urllib.request.Request(api_url, data=data)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"token {token}")
            req.add_header("User-Agent", "Fire-Crow-Security-Scanner")
            
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                success = True
                issue_url = res_data.get("html_url")
                logs.append(f"Successfully created GitHub issue: {issue_url}")
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8") if err.fp else ""
            logs.append(f"GitHub API returned HTTP {err.code}: {err_body}")
        except Exception as exc:
            logs.append(f"GitHub API connection failed: {exc}")

    pr_created = False
    pr_url = ""
    branch = ""
    ai_pr_summary = _build_ai_pr_summary(remediations or [], findings)
    
    if remediations and client.write_url:
        logs.append("Remediations available. Requesting GitMCP to create a PR...")
        pr_body = "Automated security fixes generated by Fire Crow remediation workflow."
        if ai_pr_summary:
            pr_body += f"\n\n**AI Summary:** {ai_pr_summary}\n*This summary is AI-generated; verify fixes manually.*"
        pr_res = client.call_tool("create_pull_request", {
            "owner": owner,
            "repo": repo,
            "title": "Security Remediations by Fire Crow",
            "body": pr_body,
            "head": f"security-fix-fc-{job_id[:8]}",
            "base": "main",
            "files": [{"path": rem["file"], "content": rem["fixed_code"]} for rem in remediations]
        })
        if pr_res:
            pr_created = True
            pr_url = pr_res.get("url", "")
            branch = f"security-fix-fc-{job_id[:8]}"
            logs.append(f"Successfully created GitHub PR via GitMCP: {pr_url}")
        else:
            logs.append("GitMCP 'create_pull_request' tool call failed.")

    if remediations and not pr_created:
        logs.append("Attempting to create PR directly via GitHub REST API...")
        if not token:
            logs.append("No GITHUB_TOKEN configured. Direct PR creation fallback skipped.")
        else:
            try:
                # 1. Get default branch
                repo_url_api = f"https://api.github.com/repos/{owner}/{repo}"
                repo_data, status, err_msg = _github_api_request(repo_url_api, "GET", token)
                if not repo_data:
                    raise RuntimeError(f"Failed to fetch repo details: HTTP {status} - {err_msg}")
                default_branch = repo_data.get("default_branch", "main")
                
                # 2. Get default branch commit SHA
                ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{default_branch}"
                ref_data, status, err_msg = _github_api_request(ref_url, "GET", token)
                if not ref_data:
                    raise RuntimeError(f"Failed to fetch branch ref: HTTP {status} - {err_msg}")
                base_sha = ref_data.get("object", {}).get("sha")
                if not base_sha:
                    raise RuntimeError("Could not find base branch commit SHA.")

                # 3. Create a new branch
                new_branch_name = f"security-fix-fc-{job_id[:8]}"
                create_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
                ref_payload = {
                    "ref": f"refs/heads/{new_branch_name}",
                    "sha": base_sha
                }
                ref_res, status, err_msg = _github_api_request(create_ref_url, "POST", token, ref_payload)
                if not ref_res:
                    if status == 422:
                        check_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{new_branch_name}"
                        check_res, _, _ = _github_api_request(check_ref_url, "GET", token)
                        existing_sha = check_res.get("object", {}).get("sha") if check_res else None

                        if existing_sha != base_sha:
                            import random
                            import string
                            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                            new_branch_name = f"{new_branch_name}-{suffix}"
                            ref_payload["ref"] = f"refs/heads/{new_branch_name}"
                            ref_res, status, err_msg = _github_api_request(create_ref_url, "POST", token, ref_payload)
                            if not ref_res:
                                raise RuntimeError(f"Failed to create branch with suffix: HTTP {status} - {err_msg}")
                            logs.append(f"Branch existed with different SHA. Created {new_branch_name}.")
                        else:
                            logs.append(f"Branch {new_branch_name} already exists and is up to date. Reusing.")
                    else:
                        raise RuntimeError(f"Failed to create new branch: HTTP {status} - {err_msg}")
                else:
                    logs.append(f"Successfully created branch {new_branch_name}.")

                # 4. Commit each file content
                for rem in remediations:
                    path = rem["file"]
                    fixed_code = rem["fixed_code"]
                    
                    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={default_branch}"
                    file_data, status, err_msg = _github_api_request(contents_url, "GET", token)
                    existing_sha = None
                    if file_data and "sha" in file_data:
                        existing_sha = file_data["sha"]
                    
                    base64_content = base64.b64encode(fixed_code.encode("utf-8")).decode("utf-8")
                    commit_payload = {
                        "message": f"Security remediation for {path} by Fire Crow",
                        "content": base64_content,
                        "branch": new_branch_name
                    }
                    if existing_sha:
                        commit_payload["sha"] = existing_sha
                    
                    commit_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
                    commit_res, status, err_msg = _github_api_request(commit_url, "PUT", token, commit_payload)
                    if not commit_res:
                        logs.append(f"Failed to commit fixes to {path}: HTTP {status} - {err_msg}")
                    else:
                        logs.append(f"Committed security fix to {path} on branch {new_branch_name}.")

                # 5. Create Pull Request
                from app.agents.verification_runner import verify_fix_on_branch

                pr_body = "Automated security fixes generated by Fire Crow remediation workflow."
                if remediations:
                    try:
                        verification = verify_fix_on_branch(
                            original_job_id=job_id,
                            repo_url=repo_url,
                            branch_name=new_branch_name,
                            original_finding_ids=[rem["finding_id"] for rem in remediations if "finding_id" in rem]
                        )
                        
                        rem_titles = []
                        for rem in remediations:
                            title = rem.get("title")
                            if not title:
                                title = next((f.title for f in findings if f.id == rem.get("finding_id")), "Security Fix")
                            rem_titles.append(title)
                        
                        pr_body = f"""## 🔒 Security Remediations by Fire Crow

This PR automatically fixes the following vulnerabilities:

{chr(10).join(f'- {t}' for t in rem_titles[:10])}

### ✅ Verification Results
- **Fix verified**: {'Yes ✅' if verification.get('verified') else 'No ❌'}
- **Remaining original findings**: {len(verification.get('still_present', []))}
- **New findings introduced**: {verification.get('new_findings', 0)}

[Full verification report]({verification.get('report_url', '')})
"""
                    except Exception as verify_err:
                        logs.append(f"Verification runner failed: {verify_err}")
                if ai_pr_summary:
                    pr_body += f"\n\n**AI Summary:** {ai_pr_summary}\n*This summary is AI-generated; verify fixes manually.*"

                pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
                pr_payload = {
                    "title": "Security Remediations by Fire Crow",
                    "body": pr_body,
                    "head": new_branch_name,
                    "base": default_branch
                }
                pr_res, status, err_msg = _github_api_request(pulls_url, "POST", token, pr_payload)
                if pr_res:
                    pr_created = True
                    pr_url = pr_res.get("html_url", "")
                    branch = new_branch_name
                    logs.append(f"Successfully created GitHub PR directly: {pr_url}")
                else:
                    logs.append(f"Failed to create Pull Request directly: HTTP {status} - {err_msg}")

            except Exception as e:
                logs.append(f"Direct GitHub PR creation failed: {e}")

    return {
        "github_issue_created": success,
        "github_pr_created": pr_created,
        "github_pr_url": pr_url,
        "github_branch": branch,
        "github_mcp_logs": logs
    }
