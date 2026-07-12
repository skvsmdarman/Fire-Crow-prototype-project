from typing import Any, Dict, List
from app.schemas.audit_state import Finding

def score_confidence(finding: Finding) -> Finding:
    """
    Augment a finding with a confidence score based on its source and current confidence.
    """
    if finding.confidence == "CONFIRMED":
        return finding

    source = finding.agent_source.upper()

    # Simple heuristics to boost confidence
    if source in ["EXPLOIT", "NETWORK"]:
        finding.confidence = "CONFIRMED"
    elif source in ["SEMGREP", "SAST", "IAC"]:
        # If static analysis, it's generally medium confidence unless it's a known high-signal rule
        finding.confidence = finding.confidence or "MEDIUM"
    elif source == "DEPENDENCY":
        finding.confidence = "HIGH" # OSV/Trivy are usually accurate
    else:
        finding.confidence = finding.confidence or "LOW"

    return finding


def score_findings(findings: List[Finding]) -> List[Finding]:
    """Score a list of findings."""
    scored = []
    for f in findings:
        scored.append(score_confidence(f))
    return scored


def generate_confidence_summary(scored_findings: List[Finding]) -> Dict[str, Any]:
    """Generate a summary of findings by confidence level."""
    summary = {"CONFIRMED": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in scored_findings:
        conf = (f.confidence or "LOW").upper()
        if conf in summary:
            summary[conf] += 1
    return summary
