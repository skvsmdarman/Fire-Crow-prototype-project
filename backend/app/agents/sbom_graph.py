import os
import json
from typing import Any, Dict, List
from backend.app.schemas.audit_state import AuditState

def generate_sbom(clone_path: str) -> Dict[str, Any]:
    """
    Very basic heuristic SBOM builder that parses package.json and requirements.txt
    if present to inventory dependencies.
    """
    components = []

    if not clone_path or not os.path.exists(clone_path):
        return {"components": components}

    # parse package.json
    pkg_json_path = os.path.join(clone_path, 'package.json')
    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = data.get('dependencies', {})
                dev_deps = data.get('devDependencies', {})
                for pkg, ver in deps.items():
                    components.append({"name": pkg, "version": ver, "ecosystem": "npm", "type": "direct"})
                for pkg, ver in dev_deps.items():
                    components.append({"name": pkg, "version": ver, "ecosystem": "npm", "type": "dev"})
        except Exception:
            pass

    # parse requirements.txt
    req_txt_path = os.path.join(clone_path, 'requirements.txt')
    if os.path.exists(req_txt_path):
        try:
            with open(req_txt_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('==')
                    if len(parts) == 2:
                        components.append({"name": parts[0], "version": parts[1], "ecosystem": "pypi", "type": "direct"})
                    else:
                        components.append({"name": parts[0], "version": "unknown", "ecosystem": "pypi", "type": "direct"})
        except Exception:
            pass

    return {"components": components}


def sbom_graph_body(db: Any, state: AuditState) -> Dict[str, Any]:
    sbom = generate_sbom(state.clone_path)
    components = sbom.get("components", [])

    from backend.app.orchestrator.maestro import log_agent_message
    log_agent_message(db, state.job_id, "SBOM_GRAPH", f"Generated SBOM with {len(components)} components.")

    return {
        "sbom_components": components,
        "dependency_graph": {"nodes": len(components), "edges": 0}
    }
