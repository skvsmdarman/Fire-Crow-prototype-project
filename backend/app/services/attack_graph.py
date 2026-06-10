from typing import Any, Dict
from app.schemas.audit_state import AuditState
from app.services.safe_llm import is_llm_enabled, safe_llm_call


def generate_chain_name(chain_description: str) -> str:
    if not is_llm_enabled("attack_chain_naming"):
        return "Potential Attack Path"

    prompt = (
        "Give a very short 3-5 word name for this attack chain. "
        "Respond with only the name.\n"
        f"Attack chain: {chain_description}"
    )
    name = safe_llm_call(prompt, max_tokens=15, temperature=0.3)
    if not name:
        return "Potential Attack Path"
    return " ".join(name.split())[:80]

def build_attack_graph(state: AuditState) -> Dict[str, Any]:
    """
    Correlate findings, secrets, API surface, and SBOM into a prioritized attack graph.
    """
    nodes = []
    edges = []
    chains = []

    # 1. Add API Routes as entry nodes
    for route in state.api_surface:
        node_id = f"route_{route.get('path', 'unknown')}"
        nodes.append({
            "id": node_id,
            "type": "entrypoint",
            "label": f"API Route: {route.get('path')}",
            "risk_tag": route.get("risk_tag")
        })

    # 2. Add Secrets as asset nodes
    for f in state.secret_history_findings:
        node_id = f"secret_{f.id}"
        nodes.append({
            "id": node_id,
            "type": "asset",
            "label": f.title
        })

    # 3. Add vulnerabilities
    all_vulns = (state.static_findings + state.semgrep_findings +
                 state.iac_findings + state.dependency_vulns +
                 state.authz_findings + state.cicd_findings + state.container_findings)

    for f in all_vulns:
        node_id = f"vuln_{f.id}"
        nodes.append({
            "id": node_id,
            "type": "vulnerability",
            "label": f.title,
            "severity": f.severity.value
        })

    # 4. Form basic chains
    for route in state.api_surface:
        route_path = route.get("path", "")
        # Connect IDOR findings to routes
        for f in state.authz_findings:
            if f.route == route_path or (f.file_path and f.file_path == route.get("file")):
                edges.append({
                    "source": f"route_{route_path}",
                    "target": f"vuln_{f.id}",
                    "relation": "exposes"
                })
                description = f"Public route {route_path} exposes {f.title}"
                chains.append({
                    "name": generate_chain_name(description),
                    "description": description,
                    "severity": f.severity.value,
                    "nodes": [f"route_{route_path}", f"vuln_{f.id}"]
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "chains": chains
    }

def attack_graph_body(db: Any, state: AuditState) -> Dict[str, Any]:
    graph = build_attack_graph(state)

    from app.orchestrator.maestro import log_agent_message
    log_agent_message(db, state.job_id, "ATTACK_GRAPH", f"Built attack graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.")

    # Save graph as JSON artifact
    try:
        import json
        from app.models.audit_job import AuditArtifact
        artifact = AuditArtifact(
            job_id=state.job_id,
            artifact_type="attack_graph",
            name="correlated_attack_graph",
            data_json=json.dumps(graph)
        )
        db.add(artifact)
        db.commit()
    except Exception as e:
        db.rollback()
        log_agent_message(db, state.job_id, "ATTACK_GRAPH", f"Warning: Failed to save artifact: {str(e)}")

    return {
        "attack_graph": graph,
        "attack_chains": graph.get("chains", [])
    }
