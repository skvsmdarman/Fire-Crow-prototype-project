import logging
import uuid
from typing import List, Dict, Any, Tuple
from app.schemas import Finding, Severity

logger = logging.getLogger("firecrow.agents.cross_validation")


def cross_validate_findings(
    static_findings: List[Finding],
    dynamic_findings: List[Finding],
    semgrep_findings: List[Finding],
    dependency_vulns: List[Finding],
    iac_findings: List[Finding]
) -> Tuple[List[Finding], List[str], List[Dict[str, Any]]]:
    """
    Correlates findings from static and dynamic agents.
    - If SAST flags a potential SQLi and dynamic agent confirms it, increase confidence.
    - Flags potential false positives (e.g., SAST finds a secret but it's in a test file).
    - Uses simple heuristics to reduce noise.
    
    Returns:
        Tuple of (validated_findings, false_positives, correlation_report)
    """
    all_findings = static_findings + dynamic_findings + semgrep_findings + dependency_vulns + iac_findings
    validated_findings = []
    false_positives = []
    correlation_report = []
    
    # Track findings by type for correlation
    sast_by_type = {}
    dynamic_by_type = {}
    
    for finding in static_findings + semgrep_findings:
        finding_type = _extract_finding_type(finding)
        if finding_type not in sast_by_type:
            sast_by_type[finding_type] = []
        sast_by_type[finding_type].append(finding)
    
    for finding in dynamic_findings:
        finding_type = _extract_finding_type(finding)
        if finding_type not in dynamic_by_type:
            dynamic_by_type[finding_type] = []
        dynamic_by_type[finding_type].append(finding)
    
    # Cross-validate and update confidence
    for finding in all_findings:
        finding_type = _extract_finding_type(finding)
        is_false_positive = False
        confidence_update = None
        
        # Check if finding is in a test file
        if _is_in_test_file(finding):
            is_false_positive = True
            false_positives.append(f"Finding '{finding.title}' is in a test file - likely false positive")
            correlation_report.append({
                "finding_id": finding.id,
                "action": "flagged_false_positive",
                "reason": "Located in test file"
            })
            continue
        
        # Check if finding is in commented code
        if _is_in_commented_code(finding):
            is_false_positive = True
            false_positives.append(f"Finding '{finding.title}' appears to be in commented code")
            correlation_report.append({
                "finding_id": finding.id,
                "action": "flagged_false_positive",
                "reason": "Located in commented code"
            })
            continue
        
        # Check for correlation between SAST and dynamic findings
        if finding_type in sast_by_type and finding_type in dynamic_by_type:
            confidence_update = "high"
            correlation_report.append({
                "finding_id": finding.id,
                "action": "increased_confidence",
                "reason": f"Confirmed by both static and dynamic analysis",
                "new_confidence": "high"
            })
        
        # Check if it's a vendor/node_modules finding
        if _is_in_vendor_code(finding):
            confidence_update = "low"
            correlation_report.append({
                "finding_id": finding.id,
                "action": "decreased_confidence",
                "reason": "Located in vendor/third-party code",
                "new_confidence": "low"
            })
        
        # Update finding with new confidence
        if confidence_update:
            finding.confidence = confidence_update
        
        validated_findings.append(finding)
    
    # Generate correlation summary
    correlated_count = len([r for r in correlation_report if r["action"] == "increased_confidence"])
    false_positive_count = len(false_positives)
    
    correlation_report.append({
        "summary": {
            "total_findings": len(all_findings),
            "validated_findings": len(validated_findings),
            "correlated_findings": correlated_count,
            "false_positives_flagged": false_positive_count
        }
    })
    
    logger.info(f"Cross-validation complete: {len(validated_findings)} findings validated, "
                f"{correlated_count} correlated, {false_positive_count} false positives flagged")
    
    return validated_findings, false_positives, correlation_report


def _extract_finding_type(finding: Finding) -> str:
    """Extract the type/category of a finding for correlation."""
    title_lower = (finding.title or "").lower()
    cwe_id = finding.cwe_id or ""
    
    if "sql" in title_lower or cwe_id == "CWE-89":
        return "sql_injection"
    elif "xss" in title_lower or "cross-site" in title_lower or cwe_id == "CWE-79":
        return "xss"
    elif "command" in title_lower or "exec" in title_lower or cwe_id in ("CWE-78", "CWE-95"):
        return "command_injection"
    elif "ssrf" in title_lower or cwe_id == "CWE-918":
        return "ssrf"
    elif "xxe" in title_lower or cwe_id == "CWE-611":
        return "xxe"
    elif "ssti" in title_lower or cwe_id == "CWE-1336":
        return "ssti"
    elif "secret" in title_lower or "credential" in title_lower or cwe_id == "CWE-798":
        return "secrets"
    elif "idor" in title_lower or "authorization" in title_lower:
        return "idor"
    elif "vulnerability" in title_lower or "cve" in title_lower:
        return "vulnerability"
    else:
        return "other"


def _is_in_test_file(finding: Finding) -> bool:
    """Check if finding is in a test file."""
    evidence = finding.evidence or ""
    file_paths = []
    
    # Extract file paths from evidence
    for line in evidence.split("\n"):
        if "file=" in line:
            file_path = line.split("file=")[1].split(";")[0].strip()
            file_paths.append(file_path.lower())
    
    # Also check title and description for test file indicators
    title_lower = (finding.title or "").lower()
    desc_lower = (finding.description or "").lower()
    
    test_indicators = ["test", "spec", "mock", "fixture", "example"]
    
    for path in file_paths:
        if any(indicator in path for indicator in test_indicators):
            return True
    
    if any(indicator in title_lower for indicator in test_indicators):
        return True
    
    if any(indicator in desc_lower for indicator in test_indicators):
        return True
    
    return False


def _is_in_commented_code(finding: Finding) -> bool:
    """Check if finding appears to be in commented code."""
    evidence = finding.evidence or ""
    
    # Simple heuristic: if evidence contains comment markers, might be commented code
    comment_markers = ["//", "# ", "/*", "<!--"]
    
    for marker in comment_markers:
        if marker in evidence:
            return True
    
    return False


def _is_in_vendor_code(finding: Finding) -> bool:
    """Check if finding is in vendor/third-party code."""
    evidence = finding.evidence or ""
    
    vendor_indicators = ["node_modules", "vendor", "venv", ".venv", "dist", "build"]
    
    for indicator in vendor_indicators:
        if indicator in evidence:
            return True
    
    return False
