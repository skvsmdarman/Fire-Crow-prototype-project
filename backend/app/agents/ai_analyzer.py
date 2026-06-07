import logging
import json
import socket
import urllib.request
import urllib.error
from typing import List, Tuple, Dict, Any
from backend.app.schemas import Finding, Severity
from backend.app.config import settings

logger = logging.getLogger("firecrow.agents.ai")

RETRYABLE_GEMINI_HTTP_CODES = {404, 408, 429, 500, 502, 503, 504}


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        return isinstance(exc.reason, (TimeoutError, socket.timeout)) or "timed out" in str(exc.reason).lower()
    return "timed out" in str(exc).lower()

def run_ai_analyzer(
    static_findings: List[Finding],
    dynamic_findings: List[Finding],
    dependency_findings: List[Finding],
    iac_findings: List[Finding],
    semgrep_findings: List[Finding],
) -> Tuple[List[Finding], List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Runs AI LLM Analyzer agent using Gemini API if GEMINI_API_KEY is provided.
    Deduplicates findings, filters false positives, detects attack chains, and generates remediations.
    """
    logger.info("Running AI Analyzer over all accumulated findings...")
    
    # Combine all findings
    all_findings = static_findings + dynamic_findings + dependency_findings + iac_findings + semgrep_findings
    
    # Defaults
    deduplicated: List[Finding] = all_findings
    false_positives: List[str] = []
    attack_chains: List[Dict[str, Any]] = []
    remediations: List[Dict[str, Any]] = []

    # If no findings, return early
    if not all_findings:
        return deduplicated, false_positives, attack_chains, remediations

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.info("GEMINI_API_KEY not configured.")
        if not settings.DEBUG:
            logger.info("AI Analyzer unavailable in production; returning scanner findings without simulated remediations.")
            return deduplicated, false_positives, attack_chains, remediations

        logger.info("DEBUG mode enabled. Falling back to local simulated analysis.")
        # Local mock remediation for the first finding
        remediations.append({
            "finding_id": all_findings[0].id,
            "file": "example.py",
            "original_code": "eval(user_input)",
            "fixed_code": "ast.literal_eval(user_input)"
        })
        return deduplicated, false_positives, attack_chains, remediations

    # Format findings into JSON for context
    findings_data = []
    for f in all_findings:
        findings_data.append({
            "id": f.id,
            "agent_source": f.agent_source,
            "title": f.title,
            "description": f.description,
            "severity": f.severity.value if isinstance(f.severity, Severity) else str(f.severity),
            "evidence": f.evidence,
            "remediation": f.remediation,
            "cwe_id": f.cwe_id,
            "owasp_category": f.owasp_category
        })

    prompt = f"""You are a Principal Offensive Security Engineer & Application Security Architect.
Analyze the following vulnerability findings detected by automated scanners in a repository:
{json.dumps(findings_data, indent=2)}

You must perform a rigorous security audit and triage the findings according to enterprise security standards.

Your tasks:
1. Deduplicate findings:
   - Identify and group duplicate or overlapping alerts from different scanners.
   - Keep only the single most descriptive and contextually accurate finding.
   - Merge related evidences where appropriate.

2. Filter false positives:
   - Carefully analyze code references, paths, and patterns to dismiss false positives.
   - Identify and exclude:
     * Test fixtures, test files (e.g. files under `tests/`, `test_*.py`), mock files, or sample templates, UNLESS they contain real, active, unredacted credentials.
     * False alarms from regex patterns, such as string logging, error messages (e.g., `raise RuntimeError(...)`), print statement interpolation, HTTP path parameters (e.g., `@router.delete("/path/{id}")`), or non-SQL queries (e.g., Redis delete/get operations).
   - Any findings determined to be false positives must be dismissed by adding their IDs to the "false_positives" list.

3. Re-evaluate severity and metadata:
   - Recalculate severity (critical, high, medium, low, info) based on the exploitability of the finding within the source context.
   - Standardize titles to be professional, descriptive, and non-generic.
   - Map each valid finding to the correct CWE ID (Common Weakness Enumeration) and OWASP Top 10 category.

4. Identify complex attack chains:
   - Group findings that could be combined sequentially by an attacker to gain escalated privileges or breach the system.
   - Map out the exact step-by-step logic of the attack chain.

5. Generate production-grade remediations:
   - For every verified finding, specify the target file and the precise block of vulnerable code.
   - Provide a drop-in secure code replacement using modern framework best practices (e.g., proper parameterized DB queries, safe parsing, secure token management). No placeholders.

Output your results in this exact JSON format (and ONLY output this raw JSON structure, no other text or explanation):
{{
  "deduplicated_findings": [
    {{
      "id": "original finding id",
      "title": "A precise, professional title describing the weakness",
      "severity": "critical | high | medium | low | info",
      "description": "An in-depth, security-expert explanation of the issue, detailing why it is vulnerable and how it could be exploited.",
      "evidence": "evidence string",
      "remediation": "Step-by-step developer remediation guide.",
      "cwe_id": "CWE-...",
      "owasp_category": "A01:2021-..."
    }}
  ],
  "false_positives": ["id1", "id2"],
  "attack_chains": [
    {{
      "title": "Chained Attack Path: [Title]",
      "description": "Detailed explanation of the multi-stage exploit flow.",
      "severity": "critical | high | medium",
      "chained_finding_ids": ["id_a", "id_b"]
    }}
  ],
  "remediations": [
    {{
      "finding_id": "original finding id",
      "file": "file_path_relative_to_repo",
      "original_code": "exact original code block to replace",
      "fixed_code": "exact drop-in secure code replacement"
    }}
  ]
}}
"""

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    models_to_try = [settings.GEMINI_MODEL]
    if getattr(settings, "GEMINI_ENABLE_FALLBACK_MODEL", False) and getattr(settings, "GEMINI_FALLBACK_MODEL", ""):
        models_to_try.append(settings.GEMINI_FALLBACK_MODEL)
    models_to_try = [m for m in dict.fromkeys(models_to_try) if m]
    success = False
    last_error_summary = ""

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        logger.info(f"Attempting Gemini call for AI Analyzer using model: {model_name}")
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("x-goog-api-key", api_key)
            
            with urllib.request.urlopen(req, timeout=getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30)) as response:
                res_content = response.read().decode("utf-8")
                res_json = json.loads(res_content)
                
                # Extract text response
                text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Strip markdown block formatting if present
                if text.startswith("```"):
                    lines = text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    text = "\n".join(lines).strip()
                
                parsed = json.loads(text)
                
                # Process false positives
                false_positives = parsed.get("false_positives", [])
                
                # Map deduplicated findings back to Finding schema objects
                deduplicated = []
                for item in parsed.get("deduplicated_findings", []):
                    fid = item.get("id")
                    if fid in false_positives:
                        continue
                    orig = next((x for x in all_findings if x.id == fid), None)
                    source = orig.agent_source if orig else "ai_analyzer"
                    
                    sev_str = item.get("severity", "medium").lower()
                    sev = Severity.MEDIUM
                    for val in Severity:
                        if val.value == sev_str:
                            sev = val
                            break

                    deduplicated.append(Finding(
                        id=fid,
                        agent_source=source,
                        title=item.get("title", "AI Audited Finding"),
                        description=item.get("description", ""),
                        severity=sev,
                        evidence=item.get("evidence", ""),
                        remediation=item.get("remediation", ""),
                        cwe_id=item.get("cwe_id"),
                        owasp_category=item.get("owasp_category")
                    ))

                attack_chains = parsed.get("attack_chains", [])
                remediations = parsed.get("remediations", [])
                logger.info(f"AI Analyzer finished successfully via Gemini ({model_name}). {len(deduplicated)} deduplicated findings, {len(false_positives)} false positives.")
                success = True
                break
        except urllib.error.HTTPError as err:
            last_error_summary = f"HTTP {err.code}: {err.reason}"
            if err.code in RETRYABLE_GEMINI_HTTP_CODES:
                logger.warning(
                    "Gemini model %s returned HTTP %s. Trying next fallback model.",
                    model_name,
                    err.code,
                )
                continue
            logger.exception(
                "Gemini API call failed for model %s with non-retryable status %s: %s",
                model_name,
                err.code,
                err,
            )
            break
        except Exception as exc:
            last_error_summary = str(exc)
            if _is_timeout_error(exc):
                logger.warning("Gemini model %s timed out. Trying next fallback model.", model_name)
                continue
            logger.exception("Gemini API call failed for model %s. Trying next fallback model.", model_name)
            continue

    if not success:
        if last_error_summary:
            logger.error("All Gemini models failed. Last error: %s", last_error_summary)
        else:
            logger.error("All Gemini models failed.")
        if settings.DEBUG:
            logger.info("DEBUG mode enabled. Using local simulated AI remediation.")
            remediations.append({
                "finding_id": all_findings[0].id,
                "file": "example.py",
                "original_code": "eval(user_input)",
                "fixed_code": "ast.literal_eval(user_input)"
            })

    return deduplicated, false_positives, attack_chains, remediations
