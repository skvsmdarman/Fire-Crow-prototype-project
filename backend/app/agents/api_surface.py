import os
import re
from typing import Any, Dict, List
from app.schemas.audit_state import AuditState

def detect_api_endpoints(clone_path: str) -> List[Dict[str, Any]]:
    """
    Heuristically detect API endpoints from common stacks.
    Returns a list of endpoints with metadata.
    """
    endpoints = []

    if not clone_path or not os.path.exists(clone_path):
        return endpoints

    # Fast heuristic regexes
    # FastAPI/Flask: @app.get("/path"), @router.post('/path')
    python_route_pattern = re.compile(r'@(?:app|router|bp|blueprint)\.(get|post|put|delete|patch|route)\([\'"]([^\'"]+)[\'"]')

    # Express: app.get('/path', ...), router.post("/path", ...)
    express_route_pattern = re.compile(r'(?:app|router)\.(get|post|put|delete|patch|all)\([\'"]([^\'"]+)[\'"]')

    # Django: path('route/', ...)
    django_route_pattern = re.compile(r'path\([\'"]([^\'"]+)[\'"]')

    for root, _, files in os.walk(clone_path):
        # Skip common non-source directories
        if any(skip in root.split(os.sep) for skip in ['.git', 'node_modules', 'venv', '.venv', '__pycache__', 'dist', 'build']):
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in ['.py', '.js', '.ts', '.tsx', '.jsx']:
                continue

            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, clone_path)

            # Next.js App Router (app/api/route.ts)
            if 'app/api' in rel_path.replace(os.sep, '/') and file.startswith('route.'):
                route_path = '/api/' + os.path.dirname(rel_path.replace(os.sep, '/')).split('app/api/')[-1]
                endpoints.append({
                    "path": route_path.replace('//', '/'),
                    "method": "ANY",
                    "file": rel_path,
                    "framework": "Next.js"
                })
                continue

            # Next.js Pages Router (pages/api/...)
            if 'pages/api' in rel_path.replace(os.sep, '/'):
                route_path = '/api/' + rel_path.replace(os.sep, '/').split('pages/api/')[-1].replace(ext, '')
                if route_path.endswith('/index'):
                    route_path = route_path[:-6]
                endpoints.append({
                    "path": route_path.replace('//', '/'),
                    "method": "ANY",
                    "file": rel_path,
                    "framework": "Next.js"
                })
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Python Routes
                        if ext == '.py':
                            for match in python_route_pattern.finditer(line):
                                method, path = match.groups()
                                if method == 'route': method = 'ANY'
                                endpoints.append({
                                    "path": path,
                                    "method": method.upper(),
                                    "file": rel_path,
                                    "line": line_num,
                                    "framework": "Python (FastAPI/Flask)"
                                })

                            for match in django_route_pattern.finditer(line):
                                path = match.group(1)
                                endpoints.append({
                                    "path": f"/{path}",
                                    "method": "ANY",
                                    "file": rel_path,
                                    "line": line_num,
                                    "framework": "Django"
                                })

                        # JS/TS Routes
                        elif ext in ['.js', '.ts']:
                            for match in express_route_pattern.finditer(line):
                                method, path = match.groups()
                                endpoints.append({
                                    "path": path,
                                    "method": method.upper(),
                                    "file": rel_path,
                                    "line": line_num,
                                    "framework": "Express"
                                })

            except Exception:
                continue

    return endpoints


def analyze_route_risk(endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "total_endpoints": len(endpoints),
        "high_risk_routes": 0,
        "auth_routes": 0,
        "admin_routes": 0,
        "upload_routes": 0
    }

    for ep in endpoints:
        path = ep.get("path", "").lower()
        if "admin" in path:
            summary["admin_routes"] += 1
            ep["risk_tag"] = "admin"
        elif "upload" in path:
            summary["upload_routes"] += 1
            ep["risk_tag"] = "upload"
        elif any(x in path for x in ["auth", "login", "register", "token"]):
            summary["auth_routes"] += 1
            ep["risk_tag"] = "auth"

        # IDOR risk indicators
        if re.search(r'\{.*id\}', path) or re.search(r':\w*id', path):
            ep["idor_risk"] = True

    summary["high_risk_routes"] = summary["admin_routes"] + summary["upload_routes"]
    return summary


def api_surface_body(db: Any, state: AuditState) -> Dict[str, Any]:
    endpoints = detect_api_endpoints(state.clone_path)
    risk_summary = analyze_route_risk(endpoints)

    from app.orchestrator.maestro import log_agent_message
    log_agent_message(db, state.job_id, "API_SURFACE", f"Detected {len(endpoints)} API endpoints.")

    return {
        "api_surface": endpoints,
        "route_risk_summary": risk_summary
    }
