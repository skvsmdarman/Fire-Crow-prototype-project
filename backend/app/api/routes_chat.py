from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import logging

from backend.app.models import get_db, FindingModel
from backend.app.services.auth import get_current_user
from backend.app.api.audit_queries import get_owned_job_or_404
from backend.app.services.safe_llm import is_llm_enabled, safe_llm_call

logger = logging.getLogger("firecrow.api.chat")
router = APIRouter(prefix="/chat", tags=["Security Chat"])

class ChatRequest(BaseModel):
    job_id: str
    message: str

@router.post("/ask")
async def ask_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    if not is_llm_enabled("chat_assistant"):
        raise HTTPException(status_code=503, detail="Chat assistant is disabled. Enable via feature flag.")

    job = get_owned_job_or_404(db, payload.job_id, user_id)
    
    findings = db.query(FindingModel).filter(FindingModel.job_id == payload.job_id).all()
    findings_context = []
    for f in findings:
        findings_context.append({
            "title": f.title,
            "severity": f.severity,
            "description": f.description,
            "file_path": f.file_path,
            "line_number": f.line_number,
            "evidence": f.evidence
        })
    
    prompt = f"""You are Fire Crow AI, an elite security analyst assistant.
Here are the security findings for this repository scan:
{json.dumps(findings_context, indent=2)}

The user asks: {payload.message}

Provide a concise, helpful, and highly professional response to their question or request, keeping context of these findings. Offer actionable advice or explain the vulnerability in simpler terms if requested. Keep it concise (1-3 paragraphs) unless more detail is requested. Do not output raw JSON unless requested.
"""

    try:
        text_response = safe_llm_call(prompt, max_tokens=300, temperature=0.3)
        if not text_response:
            raise HTTPException(status_code=502, detail="Chat assistant is temporarily unavailable.")
        return {"response": text_response, "answer": text_response}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to invoke Gemini for chat assistant.")
        raise HTTPException(status_code=500, detail="Chat assistant failed to respond.")
