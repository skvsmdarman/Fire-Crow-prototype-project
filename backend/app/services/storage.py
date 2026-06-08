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

from backend.app.config import settings, WORKSPACE_DIR
from backend.app.models.compliance import ArtifactObject, Membership, RetentionPolicy
from backend.app.models.user import User
from backend.app.services.redaction import redact_text

logger = logging.getLogger("firecrow.services.storage")

LOCAL_STORAGE_DIR = Path(WORKSPACE_DIR) / "workspace" / "storage"
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def calculate_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StorageService:
    def __init__(self):
        self.r2_bucket = settings.R2_BUCKET_NAME or os.getenv("CLOUDFLARE_R2_BUCKET", "firecrow-reports")
        self.r2_endpoint = settings.R2_ENDPOINT_URL or os.getenv("CLOUDFLARE_R2_ENDPOINT")
        self.r2_access_key = settings.R2_ACCESS_KEY_ID or os.getenv("CLOUDFLARE_R2_ACCESS_KEY")
        self.r2_secret_key = settings.R2_SECRET_ACCESS_KEY or os.getenv("CLOUDFLARE_R2_SECRET_KEY")

        self.s3_client = None
        if self.r2_endpoint and self.r2_access_key and self.r2_secret_key:
            try:
                import boto3  # type: ignore
                from botocore.client import Config  # type: ignore

                endpoint = self.r2_endpoint
                if endpoint and not (endpoint.startswith("http://") or endpoint.startswith("https://")):
                    endpoint = f"https://{endpoint}"

                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint,
                    aws_access_key_id=self.r2_access_key,
                    aws_secret_access_key=self.r2_secret_key,
                    config=Config(signature_version="s3v4"),
                    region_name="auto"
                )
                logger.info("StorageService S3 client initialized successfully.")
            except Exception as e:
                logger.error("Failed to initialize S3 client: %s", redact_text(str(e)))

    def is_s3_active(self) -> bool:
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
                logger.error("S3 upload failed: %s", redact_text(str(e)))
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
        
        # Admin or root bypass
        role = (user.role_id or "").lower()
        if role in {"admin", "owner", "security_admin", "platform_admin"}:
            return True

        if user.tenant_id == organization_id:
            return True

        # Check memberships
        membership = db.query(Membership).filter(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id
        ).first()
        return membership is not None

    def get_presigned_url(self, db: Session, artifact_id: str, user_id: str, expires_in: int = 3600) -> str:
        """
        Generates short-lived presigned URL or returns local retrieval URL after verifying access.
        """
        artifact = db.query(ArtifactObject).filter(
            ArtifactObject.id == artifact_id,
            ArtifactObject.deletion_status == "active"
        ).first()
        
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found or deleted")

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this artifact")

        if artifact.storage_provider == "cloudflare_r2" and self.s3_client is not None:
            try:
                url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": artifact.bucket_name, "Key": artifact.object_key},
                    ExpiresIn=expires_in
                )
                return url
            except Exception as e:
                logger.error("Failed to generate presigned S3 URL: %s", redact_text(str(e)))

        # Fallback/Local retrieval URL
        return f"/api/v1/storage/artifacts/{artifact_id}/download"

    def download_artifact_local(self, db: Session, artifact_id: str, user_id: str) -> tuple[Path, str, str]:
        """
        Retrieve local file path, filename, and media type after verifying access.
        """
        artifact = db.query(ArtifactObject).filter(
            ArtifactObject.id == artifact_id,
            ArtifactObject.deletion_status == "active"
        ).first()

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found or deleted")

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this artifact")

        if artifact.storage_provider == "cloudflare_r2" and self.s3_client is not None:
            # Download file from R2 to a temp cache location and serve
            try:
                cache_dir = LOCAL_STORAGE_DIR / "cache"
                cache_dir.mkdir(exist_ok=True)
                temp_path = cache_dir / f"{artifact.id}-{os.path.basename(artifact.object_key)}"
                
                if not temp_path.exists():
                    self.s3_client.download_file(artifact.bucket_name, artifact.object_key, str(temp_path))
                
                return temp_path, os.path.basename(artifact.object_key), artifact.mime_type or "application/octet-stream"
            except Exception as e:
                logger.error("Failed downloading R2 object: %s", redact_text(str(e)))
                raise HTTPException(status_code=500, detail="Failed to fetch object from remote storage")

        # Local storage direct path
        file_path = LOCAL_STORAGE_DIR / artifact.object_key
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Artifact file not found on disk")

        return file_path, os.path.basename(artifact.object_key), artifact.mime_type or "application/octet-stream"

    def set_legal_hold(self, db: Session, artifact_id: str, hold: bool, user_id: str) -> ArtifactObject:
        """
        Sets legal hold on an artifact to prevent deletion.
        """
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this artifact")

        artifact.legal_hold = hold
        artifact.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(artifact)

        logger.warning("Legal hold set to %s on artifact %s by user %s", hold, artifact_id, user_id)
        return artifact

    def delete_artifact(self, db: Session, artifact_id: str, user_id: str, force: bool = False) -> bool:
        """
        Delete artifact from storage and mark as deleted in DB, respecting legal holds.
        """
        artifact = db.query(ArtifactObject).filter(ArtifactObject.id == artifact_id).first()
        if not artifact:
            return False

        if not self.verify_tenant_access(db, user_id, artifact.organization_id):
            raise HTTPException(status_code=403, detail="Access denied to this artifact")

        if artifact.legal_hold and not force:
            raise HTTPException(status_code=400, detail="Cannot delete artifact under active legal hold")

        success = True
        if artifact.storage_provider == "cloudflare_r2" and self.s3_client is not None:
            try:
                self.s3_client.delete_object(Bucket=artifact.bucket_name, Key=artifact.object_key)
            except Exception as e:
                logger.error("Failed to delete object from S3: %s", redact_text(str(e)))
                success = False
        else:
            file_path = LOCAL_STORAGE_DIR / artifact.object_key
            if file_path.exists():
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error("Failed to delete local file: %s", redact_text(str(e)))
                    success = False

        if success or force:
            artifact.deletion_status = "deleted"
            artifact.deleted_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False


# Global storage service instance
storage_service = StorageService()
