import logging
from typing import Any, Dict, List, Tuple

from app.schemas import Finding, Severity

logger = logging.getLogger("firecrow.agents.ai")

_SEVERITY_RANK = {
    Severity.CRITICAL: 4,
    Severity.HIGH: 3,
    Severity.MEDIUM: 2,
    Severity.LOW: 1,
    Severity.INFO: 0,
}


def _finding_identity(finding: Finding) -> tuple[str, str, int, str]:
    return (
        finding.title.strip().lower(),
        (finding.file_path or "").strip().lower(),
        finding.line_number or -1,
        (finding.route or "").strip().lower(),
    )


def _finding_quality(finding: Finding) -> tuple[int, int]:
    content_score = len(finding.description or "") + len(finding.evidence or "") + len(finding.remediation or "")
    return (_SEVERITY_RANK.get(finding.severity, 0), content_score)


def _merge_text(primary: str | None, secondary: str | None) -> str | None:
    values = [value.strip() for value in (primary, secondary) if value and value.strip()]
    if not values:
        return None
    if len(values) == 1 or values[0] == values[1]:
        return values[0]
    return "\n\n".join(dict.fromkeys(values))


def _merge_findings(existing: Finding, candidate: Finding) -> Finding:
    preferred, other = (existing, candidate)
    if _finding_quality(candidate) > _finding_quality(existing):
        preferred, other = candidate, existing

    return preferred.model_copy(
        update={
            "evidence": _merge_text(preferred.evidence, other.evidence),
            "remediation": preferred.remediation or other.remediation,
            "cwe_id": preferred.cwe_id or other.cwe_id,
            "owasp_category": preferred.owasp_category or other.owasp_category,
            "confidence": preferred.confidence or other.confidence,
            "scanner_name": preferred.scanner_name or other.scanner_name,
            "scanner_mode": preferred.scanner_mode or other.scanner_mode,
            "metadata_json": preferred.metadata_json or other.metadata_json,
        }
    )


def _sort_findings(findings: List[Finding]) -> List[Finding]:
    return sorted(
        findings,
        key=lambda finding: (
            _SEVERITY_RANK.get(finding.severity, 0),
            finding.title.lower(),
            (finding.file_path or "").lower(),
            finding.line_number or -1,
        ),
        reverse=True,
    )


def run_ai_analyzer(
    static_findings: List[Finding],
    dynamic_findings: List[Finding],
    dependency_findings: List[Finding],
    iac_findings: List[Finding],
    semgrep_findings: List[Finding],
) -> Tuple[List[Finding], List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Deterministic analyzer for core security output.
    LLM-based deduplication, severity changes, and remediation generation are disabled by policy.
    """
    logger.info("Running deterministic analyzer over accumulated findings. Core security decisions are LLM-disabled.")

    all_findings = static_findings + dynamic_findings + dependency_findings + iac_findings + semgrep_findings
    if not all_findings:
        return [], [], [], []

    deduplicated_by_key: dict[tuple[str, str, int, str], Finding] = {}
    for finding in all_findings:
        identity = _finding_identity(finding)
        current = deduplicated_by_key.get(identity)
        deduplicated_by_key[identity] = _merge_findings(current, finding) if current else finding

    deduplicated = _sort_findings(list(deduplicated_by_key.values()))
    logger.info(
        "Deterministic analyzer retained %s of %s findings. No LLM remediations or false-positive suppression were applied.",
        len(deduplicated),
        len(all_findings),
    )
    return deduplicated, [], [], []


def ai_analyzer_body(db, state):
    try:
        dedup, fps, chains, rems = run_ai_analyzer(
            state.static_findings,
            state.dynamic_findings,
            state.dependency_vulns,
            state.iac_findings,
            state.semgrep_findings,
        )
        return {
            "deduplicated_findings": dedup,
            "false_positives": fps,
            "attack_chains": chains,
            "remediations": rems,
        }
    except Exception:
        logger.exception("Deterministic analyzer failed.")
        raise
