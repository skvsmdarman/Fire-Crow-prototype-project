import logging
import json
import urllib.request
import urllib.error
from typing import List, Tuple, Dict, Any
from backend.app.schemas import Finding, Severity
from backend.app.config import settings

logger = logging.getLogger("firecrow.agents.ai")

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

    prompt = f"""You are an advanced AI Security Auditor. Analyze these vulnerability findings detected in a repository:
{json.dumps(findings_data, indent=2)}

Your tasks:
1. Deduplicate findings: Group duplicate alerts from different scanners. Keep the one that is most descriptive.
2. Filter false positives: Identify and dismiss issues that are false positives (e.g. comments, test fixtures, already rotated or harmless values). Place their IDs in false_positives.
3. Identify attack chains: Find how multiple findings might be chained together to create a higher impact attack path.
4. Generate secure code remediations: For each real vulnerability, identify the file path, the code block, and write the drop-in replacement (fix).

Output your results in this exact JSON format (and ONLY output this raw JSON structure, no other text or explanation):
{{
  "deduplicated_findings": [
    {{
      "id": "original finding id",
      "title": "Cleaned up title",
      "severity": "critical | high | medium | low | info",
      "description": "Deduplicated/improved description",
      "evidence": "evidence string",
      "remediation": "remediation description",
      "cwe_id": "CWE-...",
      "owasp_category": "..."
    }}
  ],
  "false_positives": ["id1", "id2"],
  "attack_chains": [
    {{
      "title": "Chain description",
      "description": "How the vulnerabilities chain together",
      "severity": "high",
      "chained_finding_ids": ["id_a", "id_b"]
    }}
  ],
  "remediations": [
    {{
      "finding_id": "original finding id",
      "file": "file_path_relative_to_repo",
      "original_code": "code block to find",
      "fixed_code": "replacement code block"
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

    models_to_try = list(dict.fromkeys([
        settings.GEMINI_MODEL, 
        "gemini-3.5-flash", 
        "gemini-3.0-flash", 
        "gemini-2.5-flash", 
        "gemini-2.0-flash", 
        "gemini-1.5-flash"
    ]))
    success = False

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        logger.info(f"Attempting Gemini call for AI Analyzer using model: {model_name}")
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data)
            req.add_header("Content-Type", "application/json")
            req.add_header("x-goog-api-key", api_key)
            
            with urllib.request.urlopen(req, timeout=30) as response:
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
            if err.code == 404:
                logger.warning(f"Model {model_name} returned 404. Trying next fallback model...")
                continue
            else:
                logger.exception(f"Gemini API call failed for model {model_name} with status {err.code}: {err}")
                break
        except Exception as exc:
            logger.exception(f"Gemini API call failed for model {model_name}: {exc}")
            break

    if not success:
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
