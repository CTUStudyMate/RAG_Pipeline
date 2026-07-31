"""Internal document-processing endpoint used by MainBackend."""

import hmac
import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.workers.document_tasks import process_document


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

router = APIRouter(prefix="/internal/documents", tags=["internal-documents"])


class ProcessDocumentRequest(BaseModel):
    document_id: int = Field(gt=0)
    processing_run_id: UUID


def require_service_token(
    x_internal_service_token: str | None,
) -> None:
    expected_token = os.getenv("INTERNAL_API_SERVICE_TOKEN")
    if not expected_token or not x_internal_service_token or not hmac.compare_digest(
        expected_token,
        x_internal_service_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token.",
        )


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
def enqueue_document_processing(
    request: ProcessDocumentRequest,
    x_internal_service_token: str | None = Header(default=None),
) -> dict[str, str | int]:
    require_service_token(x_internal_service_token)

    task = process_document.apply_async(
        args=[request.document_id, str(request.processing_run_id)],
        task_id=str(request.processing_run_id),
    )
    return {
        "document_id": request.document_id,
        "processing_run_id": str(request.processing_run_id),
        "task_id": task.id,
        "status": "queued",
    }
