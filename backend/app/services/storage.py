from __future__ import annotations

import hashlib
import logging
import mimetypes
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import WORKSPACE_DIR
from app.models.compliance import ArtifactObject, Membership, RetentionPolicy
from app.models.user import User

logger = logging.getLogger("firecrow.services.storage")

LOCAL_STORAGE_DIR = Path(WORKSPACE_DIR) / "workspace" / "storage"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StorageService:
    def __init__(self):
        self.storage_root = LOCAL_STORAGE_DIR

    @property
    def s3_client(self):
        return None

    def is_s3_active(self) -> bool:
        return False

    def upload_artifact(
        self,
        db: Session,
        file_data: bytes | Path,
        organization_id: str,
        artifact_type: str,
        file_name: str,
        user_id: Optional[str] = None,
        job_id: Optional[str] = None,
        sensitivity_level: str = "internal",
    ) -> ArtifactObject:
        """
        Store an artifact on the local workspace while keeping metadata in the database.
        """
        if isinstance(file_data, Path):
            data = file_data.read_bytes()
        else:
            data = file_data

        size_bytes = len(data)
        sha256_hash = calculate_sha256(data)
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"

        retention_until = None
        policy = db.query(RetentionPolicy).filter(RetentionPolicy.data_category == artifact_type).first()
        if not policy:
            policy = db.query(RetentionPolicy).filter(RetentionPolicy.is_default == True).first()
        if policy:
            retention_until = datetime.now(timezone.utc) + timedelta(days=policy.retention_days)

        unique_id = str(uuid.uuid4())
        safe_file_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        object_key = f"tenants/{organization_id}/{artifact_type}/{unique_id}-{safe_file_name}"
        self._write_local_file(object_key, data)

        artifact = ArtifactObject(
            id=unique_id,
            organization_id=organization_id,
            job_id=job_id,
            object_key=object_key,
            bucket_name="workspace-storage",
            storage_provider="local_db",
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            artifact_type=artifact_type,
            sensitivity_level=sensitivity_level,
            created_by_user_id=user_id,
            retention_policy_id=policy.id if policy else None,
            retention_until=retention_until,
            deletion_status="active",
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        logger.info("Artifact metadata saved: ID %s, SHA256 %s", artifact.id, sha256_hash)
        return artifact

    def _write_local_file(self, object_key: str, data: bytes) -> None:
        target_path = self.storage_root / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        logger.info("Stored artifact locally at %s", target_path)

    def verify_tenant_access(self, db: Session, user_id: str, organization_id: str) -> bool:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        if user.is_admin:
            return True

        if user.tenant_id and user.tenant_id == organization_id:
            return True

        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        ).first()
        return membership is not None

    def get_artifact(self, db: Session, artifact_id: str, user_id: str) -> Optional[tuple[ArtifactObject, Any]]:
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            return None

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            has_job_access = False
            if artifact.job_id:
                try:
                    from app.api.audit_queries import get_owned_job_or_404

                    get_owned_job_or_404(db, artifact.job_id, user_id)
                    has_job_access = True
                except Exception:
                    pass
            if not has_job_access:
                raise HTTPException(status_code=403, detail="Not authorized to access this artifact")

        local_path = self.storage_root / artifact.object_key
        if not local_path.exists():
            logger.error("Local artifact not found: %s", local_path)
            return None
        return artifact, local_path

    def download_artifact_local(self, db: Session, artifact_id: str, user_id: str):
        result = self.get_artifact(db, artifact_id, user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Artifact not found")
        artifact, file_path = result
        return file_path, artifact.object_key.split("/")[-1], artifact.mime_type

    def delete_artifact(self, db: Session, artifact_id: str, user_id: str) -> bool:
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            return False

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            has_job_access = False
            if artifact.job_id:
                try:
                    from app.api.audit_queries import get_owned_job_or_404

                    get_owned_job_or_404(db, artifact.job_id, user_id)
                    has_job_access = True
                except Exception:
                    pass
            if not has_job_access:
                raise HTTPException(status_code=403, detail="Not authorized to delete this artifact")

        artifact.deletion_status = "pending_deletion"
        artifact.deleted_at = datetime.now(timezone.utc)
        db.commit()

        self._hard_delete_file(artifact)

        artifact.deletion_status = "deleted"
        db.commit()
        return True

    def set_legal_hold(self, db: Session, artifact_id: str, hold: bool, user_id: str) -> ArtifactObject:
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Not authorized to update this artifact")

        artifact.legal_hold = hold
        db.commit()
        db.refresh(artifact)
        return artifact

    def _hard_delete_file(self, artifact: ArtifactObject) -> None:
        local_path = self.storage_root / artifact.object_key
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception as exc:
                logger.error("Failed to delete local file %s: %s", local_path, exc)


storage_service = StorageService()
