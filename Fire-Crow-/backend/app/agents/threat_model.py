import logging
import uuid
from typing import List, Dict, Any, Optional
from app.schemas import Finding, Severity

logger = logging.getLogger("firecrow.agents.threat_model")


def generate_threat_model(
    tech_stack: List[str],
    entry_points: List[str],
    dependency_manifests: List[str],
    api_surface: List[Dict[str, Any]],
    repo_security: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a prioritized list of assets and attack vectors based on tech stack and entry points.
    Adjusts the scan plan dynamically based on detected technologies.
    """
    threats = []
    assets = []
    attack_vectors = []
    
    # Identify assets based on tech stack
    for tech in tech_stack:
        tech_lower = tech.lower()
        
        if "python" in tech_lower or "fastapi" in tech_lower or "django" in tech_lower:
            assets.append({
                "type": "backend_api",
                "technology": tech,
                "risk_level": "high",
                "attack_vectors": ["sql_injection", "command_injection", "deserialization"]
            })
            attack_vectors.extend(["sql_injection", "command_injection"])
        
        if "node" in tech_lower or "express" in tech_lower:
            assets.append({
                "type": "backend_api",
                "technology": tech,
                "risk_level": "high",
                "attack_vectors": ["prototype_pollution", "nosql_injection", "rce"]
            })
            attack_vectors.extend(["prototype_pollution", "nosql_injection"])
        
        if "react" in tech_lower or "next" in tech_lower or "vue" in tech_lower:
            assets.append({
                "type": "frontend",
                "technology": tech,
                "risk_level": "medium",
                "attack_vectors": ["xss", "csrf", "client_side_injection"]
            })
            attack_vectors.extend(["xss", "csrf"])
        
        if "docker" in tech_lower:
            assets.append({
                "type": "container",
                "technology": tech,
                "risk_level": "high",
                "attack_vectors": ["container_escape", "privilege_escalation", "image_vulnerabilities"]
            })
            attack_vectors.extend(["container_escape", "privilege_escalation"])
        
        if "kubernetes" in tech_lower or "k8s" in tech_lower:
            assets.append({
                "type": "orchestration",
                "technology": tech,
                "risk_level": "critical",
                "attack_vectors": ["rbac_misconfiguration", "secrets_exposure", "pod_escape"]
            })
            attack_vectors.extend(["rbac_misconfiguration", "secrets_exposure"])
        
        if "terraform" in tech_lower or "aws" in tech_lower:
            assets.append({
                "type": "infrastructure",
                "technology": tech,
                "risk_level": "high",
                "attack_vectors": ["iam_misconfiguration", "s3_exposure", "privilege_escalation"]
            })
            attack_vectors.extend(["iam_misconfiguration", "s3_exposure"])
    
    # Identify entry points
    for entry in entry_points:
        entry_lower = entry.lower()
        
        if entry_lower.endswith(".py") or entry_lower.endswith(".js"):
            attack_vectors.append("code_execution")
        
        if "dockerfile" in entry_lower:
            attack_vectors.append("container_misconfiguration")
        
        if "docker-compose" in entry_lower:
            attack_vectors.append("service_exposure")
    
    # Check API surface for additional threats
    if api_surface:
        for endpoint in api_surface:
            path = endpoint.get("path", "").lower()
            
            if "/api/" in path:
                attack_vectors.append("api_abuse")
            
            if any(param in path for param in ["id", "user", "admin"]):
                attack_vectors.append("idor")
            
            if "upload" in path or "file" in path:
                attack_vectors.append("file_upload_vulnerability")
    
    # Check repo security findings
    if repo_security and repo_security.get("repo_security_findings"):
        for finding in repo_security["repo_security_findings"]:
            finding_type = finding.get("type", "")
            
            if "branch_protection" in finding_type:
                threats.append({
                    "type": "weak_access_controls",
                    "severity": "high",
                    "description": "Weak branch protection rules allow unauthorized code changes",
                    "mitigation": "Enable branch protection with required reviews"
                })
            
            if "secret_scanning" in finding_type:
                threats.append({
                    "type": "secret_exposure_risk",
                    "severity": "medium",
                    "description": "Secret scanning is disabled, increasing risk of credential leaks",
                    "mitigation": "Enable secret scanning alerts"
                })
    
    # Deduplicate attack vectors
    attack_vectors = list(set(attack_vectors))
    
    # Generate prioritized scan recommendations
    scan_recommendations = []
    
    if "sql_injection" in attack_vectors:
        scan_recommendations.append({
            "test_type": "sql_injection_deep",
            "priority": "critical",
            "description": "Deep SQL injection testing on database-connected endpoints"
        })
    
    if "command_injection" in attack_vectors:
        scan_recommendations.append({
            "test_type": "command_injection_deep",
            "priority": "critical",
            "description": "Command injection testing on user input handling"
        })
    
    if "xss" in attack_vectors:
        scan_recommendations.append({
            "test_type": "xss_deep",
            "priority": "high",
            "description": "Cross-site scripting testing on all user inputs"
        })
    
    if "idor" in attack_vectors:
        scan_recommendations.append({
            "test_type": "idor_deep",
            "priority": "high",
            "description": "Insecure Direct Object Reference testing on API endpoints"
        })
    
    if "container_escape" in attack_vectors or "container_misconfiguration" in attack_vectors:
        scan_recommendations.append({
            "test_type": "container_security_deep",
            "priority": "high",
            "description": "Container security misconfiguration testing"
        })
    
    if "secrets_exposure" in attack_vectors:
        scan_recommendations.append({
            "test_type": "secrets_deep",
            "priority": "high",
            "description": "Deep secrets scanning including environment variables and config files"
        })
    
    threat_model = {
        "assets": assets,
        "attack_vectors": attack_vectors,
        "threats": threats,
        "scan_recommendations": scan_recommendations,
        "risk_summary": {
            "total_assets": len(assets),
            "high_risk_assets": len([a for a in assets if a.get("risk_level") in ("high", "critical")]),
            "total_attack_vectors": len(attack_vectors),
            "total_threats": len(threats),
            "total_scan_recommendations": len(scan_recommendations)
        }
    }
    
    logger.info(f"Threat model generated: {len(assets)} assets, {len(attack_vectors)} attack vectors, {len(threats)} threats")
    
    return threat_model
