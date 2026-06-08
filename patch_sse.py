import re

with open("backend/app/api/routes_sse.py", "r") as f:
    content = f.read()

progress_logic = """
                # Fetch new logs
                new_logs = (
                    loop_db.query(AgentLog)
                    .filter(AgentLog.job_id == job_id, AgentLog.id > last_seen_log_id)
                    .order_by(AgentLog.id.asc())
                    .all()
                )

                # Map progress deterministically
                def get_progress(status_val, current_agent):
                    if status_val in ["completed"]: return 100
                    if status_val in ["failed", "cancelled"]: return 100 # Frontend will handle state

                    mapping = {
                        "MAESTRO": 5,
                        "RECON": 15,
                        "SANDBOX": 25,
                        "SAST": 40,
                        "DEPENDENCY": 50,
                        "IAC": 55,
                        "ATTACK": 60,
                        "API_SURFACE": 65,
                        "AI_ANALYZER": 75,
                        "REPORTER": 90,
                        "STORAGE": 95
                    }
                    return mapping.get(current_agent, 50)

                for log in new_logs:
                    prog = get_progress(current_job.status.value, log.agent_name)

                    payload = {
                        "id": log.id,
                        "agent_name": log.agent_name,
                        "log_level": log.log_level,
                        "message": log.message,
                        "timestamp": log.timestamp.isoformat(),
                        "progress": prog,
                        "stage": log.agent_name.lower()
                    }
                    yield f"event: log\\ndata: {json.dumps(payload)}\\n\\n"
                    last_seen_log_id = log.id
"""

content = re.sub(
    r'# Fetch new logs.*?last_seen_log_id = log.id',
    progress_logic.strip(),
    content,
    flags=re.DOTALL
)

with open("backend/app/api/routes_sse.py", "w") as f:
    f.write(content)
