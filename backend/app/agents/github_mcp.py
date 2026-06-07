import logging
import re
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.schemas import Finding, Severity

logger = logging.getLogger("firecrow.agents.github_mcp")


def _github_api_request(url: str, method: str, token: str, payload: dict | None = None) -> tuple[Any, int, str]:
    import urllib.request
    import urllib.error
    import json
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
        body += f"#### {idx}. {_escape_markdown_text(finding.title)} ({severity_label})\n"
        body += f"- **Source**: {_escape_markdown_text(finding.agent_source)}\n"
        if finding.cwe_id:
            body += f"- **CWE**: {_escape_markdown_text(finding.cwe_id)}\n"
        body += f"- **Description**: {_escape_markdown_text(finding.description)}\n"
        if finding.evidence:
            body += f"- **Evidence/Proof**:\n\n{_code_block(finding.evidence)}\n"
        if finding.remediation:
            body += f"- **Remediation Plan**: {_escape_markdown_text(finding.remediation)}\n"
        body += "\n---\n"

    body += "\n\n*Report generated automatically by Fire Crow Orchestration Engine.*"
    return body

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
        logger.info(f"Connecting to GitMCP SSE endpoint: {self.sse_url}")
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
                            logger.info(f"Discovered GitMCP write endpoint: {self.write_url}")
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
                    logger.error(f"MCP tool call returned error: {res_data['error']}")
                    return None
                return res_data.get("result")
        except Exception as exc:
            logger.error(f"Failed to invoke GitMCP tool {tool_name}: {exc}")
        return None

def run_github_mcp(job_id: str, repo_url: str, findings: List[Finding], remediations: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """
    Main entry point for GITHUB_MCP agent.
    Connects to the repository's gitmcp.io remote server to raise issues/PRs.
    Falls back to direct GitHub API if gitmcp.io is unreachable or unauthenticated.
    """
    # 1. Parse repository details
    repo_info = parse_repo_url(repo_url)
    if not repo_info:
        logger.warning(f"Unsupported git URL for GitHub integration: {repo_url}")
        return {
            "github_issue_created": False,
            "github_pr_created": False,
            "github_mcp_logs": ["Unsupported repository URL format."]
        }

    owner, repo = repo_info
    logs = [f"Initiated GitHub MCP agent for {owner}/{repo}"]

    # 2. Check mock/debug
    is_mock = "example/" in repo_url or settings.DEBUG and not settings.GITHUB_TOKEN
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

    # 3. Format findings
    issue_title = "Fire Crow Security Scan Report"
    issue_body = format_findings_markdown(repo_url, findings)

    # 4. Attempt GitMCP connection
    token = settings.GITHUB_TOKEN
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
            "body": issue_body
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

    # 5. Fallback to GitHub REST API directly
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
                "body": issue_body
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
    
    if remediations and client.write_url:
        logs.append(f"Remediations available. Requesting GitMCP to create a PR...")
        pr_res = client.call_tool("create_pull_request", {
            "owner": owner,
            "repo": repo,
            "title": "Security Remediations by Fire Crow",
            "body": "Automated security fixes generated by Fire Crow AI Analyzer.",
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
                        logs.append(f"Branch {new_branch_name} already exists. Reusing branch.")
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
                pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
                pr_payload = {
                    "title": "Security Remediations by Fire Crow",
                    "body": "Automated security fixes generated by Fire Crow AI Analyzer.",
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
