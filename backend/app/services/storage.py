from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings, WORKSPACE_DIR, _global_state
from backend.app.models.compliance import ArtifactObject, Membership, RetentionPolicy
from backend.app.models.user import User
from backend.app.services.redaction import redact_text
from backend.app.services.reporter import _is_r2_auth_error

logger = logging.getLogger("firecrow.services.storage")

LOCAL_STORAGE_DIR = Path(WORKSPACE_DIR) / "workspace" / "storage"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StorageService:
    def __init__(self):
        self.r2_bucket = settings.R2_BUCKET_NAME or os.getenv("CLOUDFLARE_R2_BUCKET", "firecrow-reports")
        self.s3_client = None
        self._s3_disabled = False
        if settings.R2_ENDPOINT_URL and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY:
            try:
                import boto3
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.R2_ENDPOINT_URL,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                )
            except Exception as e:
                logger.error("Failed to initialize S3 client: %s", str(e))


    def is_s3_active(self) -> bool:
        if self._s3_disabled or _global_state.get("r2_disabled", False):
            return False
        return self.s3_client is not None

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
        Uploads an artifact to R2 or local storage, calculates SHA256, and stores DB metadata.
        """
        # Read data and compute size and SHA-256
        if isinstance(file_data, Path):
            with open(file_data, "rb") as f:
                data = f.read()
        else:
            data = file_data

        size_bytes = len(data)
        sha256_hash = calculate_sha256(data)
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Check retention policies to compute retention_until
        retention_until = None
        policy = db.query(RetentionPolicy).filter(RetentionPolicy.data_category == artifact_type).first()
        if not policy:
            policy = db.query(RetentionPolicy).filter(RetentionPolicy.is_default == True).first()
        if policy:
            retention_until = datetime.now(timezone.utc) + timedelta(days=policy.retention_days)

        # Generate structured key
        unique_id = str(uuid.uuid4())
        safe_file_name = "".join(c for c in file_name if c.isalnum() or c in "._-")
        object_key = f"tenants/{organization_id}/{artifact_type}/{unique_id}-{safe_file_name}"

        if _global_state.get("r2_disabled", False):
            self.s3_client = None

        if self.s3_client is not None:
            try:
                logger.info("Uploading artifact key '%s' to S3/R2", object_key)
                self.s3_client.put_object(
                    Bucket=self.r2_bucket,
                    Key=object_key,
                    Body=data,
                    ContentType=mime_type
                )
                storage_provider = "cloudflare_r2"
            except Exception as e:
                err_msg = str(e)
                logger.error("S3 upload failed: %s", redact_text(err_msg))
                if _is_r2_auth_error(err_msg):
                    logger.warning("R2 authentication/credentials invalid. Disabling S3 client for this session.")
                    _global_state["r2_disabled"] = True
                    self._s3_disabled = True
                    self.s3_client = None
                
                from backend.app.config import settings
                if getattr(settings, "REPORT_LOCAL_FALLBACK", True):
                    logger.info("Falling back to local storage")
                    self._write_local_file(object_key, data)
                    storage_provider = "local"
                else:
                    raise HTTPException(status_code=500, detail="Cloud storage upload failed and local fallback is disabled.")
        else:
            from backend.app.config import settings
            if getattr(settings, "REPORT_LOCAL_FALLBACK", True):
                self._write_local_file(object_key, data)
                storage_provider = "local"
            else:
                logger.error("Cloud storage not configured and local fallback is disabled.")
                raise HTTPException(status_code=500, detail="Cloud storage not configured and local fallback is disabled.")
        # Save to DB
        artifact = ArtifactObject(
            id=unique_id,
            organization_id=organization_id,
            job_id=job_id,
            object_key=object_key,
            bucket_name=self.r2_bucket if storage_provider == "cloudflare_r2" else "local",
            storage_provider=storage_provider,
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
        target_path = LOCAL_STORAGE_DIR / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(data)
        logger.info("Stored artifact locally at %s", target_path)

    def verify_tenant_access(self, db: Session, user_id: str, organization_id: str) -> bool:
        """
        Verify if the user has access to the specified tenant/organization.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        if user.role in ["admin", "superadmin"]:
            return True
            
        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id
        ).first()
        return membership is not None

    def get_artifact(self, db: Session, artifact_id: str, user_id: str) -> Optional[tuple[ArtifactObject, Any]]:
        """
        Retrieves an artifact's metadata and its data stream/file path.
        """
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            return None

        # Verify access
        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Not authorized to access this artifact")

        # Get file data based on storage provider
        if artifact.storage_provider == "cloudflare_r2" and self.s3_client is not None:
            # Download file from R2 to a temp cache location and serve
            cache_path = LOCAL_STORAGE_DIR / "cache" / artifact.object_key
            if not cache_path.exists():
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    self.s3_client.download_file(self.r2_bucket, artifact.object_key, str(cache_path))
                except Exception as e:
                    logger.error("Failed downloading R2 object: %s", redact_text(str(e)))
                    raise HTTPException(status_code=500, detail="Failed to retrieve file from cloud storage")
            return artifact, cache_path
        else:
            # Local storage
            local_path = LOCAL_STORAGE_DIR / artifact.object_key
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
        """
        Soft deletes an artifact from DB and optionally queues for hard deletion.
        """
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            return False

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this artifact")

        artifact.deletion_status = "pending_deletion"
        artifact.deleted_at = datetime.now(timezone.utc)
        db.commit()

        # Depending on compliance needs, we could either leave it for a background job
        # or delete immediately from S3/local
        # For simplicity, we just delete immediately here as a soft-delete demo is enough, 
        # but in a strict compliant environment, the actual file is shredded asynchronously.
        self._hard_delete_file(artifact)

        artifact.deletion_status = "deleted"
        db.commit()
        return True
        
    def _hard_delete_file(self, artifact: ArtifactObject) -> None:
        if artifact.storage_provider == "cloudflare_r2" and self.s3_client is not None:
            try:
                self.s3_client.delete_object(Bucket=self.r2_bucket, Key=artifact.object_key)
            except Exception as e:
                logger.error("Failed to delete object from R2: %s", redact_text(str(e)))
        else:
            local_path = LOCAL_STORAGE_DIR / artifact.object_key
            if local_path.exists():
                try:
                    # Secure deletion could be implemented here (e.g., overwriting with zeros before unlink)
                    local_path.unlink()
                except Exception as e:
                    logger.error("Failed to delete local file: %s", redact_text(str(e)))

storage_service = StorageService()
