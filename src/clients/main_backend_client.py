"""Authenticated client for MainBackend's internal document API."""

import os
from pathlib import Path
from uuid import UUID

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class MainBackendClient:
    def __init__(self) -> None:
        self._base_url = os.getenv("MAIN_BACKEND_URL", "").rstrip("/")
        self._service_token = os.getenv("INTERNAL_API_SERVICE_TOKEN", "")
        if not self._base_url or not self._service_token:
            raise RuntimeError(
                "MAIN_BACKEND_URL and INTERNAL_API_SERVICE_TOKEN must be configured."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Internal-Service-Token": self._service_token}

    def download_document(self, document_id: int, target_path: Path) -> None:
        endpoint = f"{self._base_url}/internal/documents/{document_id}/content"
        with httpx.stream(
            "GET",
            endpoint,
            headers=self._headers,
            timeout=httpx.Timeout(300.0, connect=15.0),
            follow_redirects=False,
        ) as response:
            response.raise_for_status()
            with target_path.open("wb") as target_file:
                for chunk in response.iter_bytes():
                    target_file.write(chunk)

    def update_status(
        self,
        document_id: int,
        processing_run_id: UUID,
        status: str,
        progress: int,
        message: str,
    ) -> None:
        endpoint = f"{self._base_url}/internal/documents/{document_id}/processing-status"
        response = httpx.post(
            endpoint,
            headers=self._headers,
            json={
                "processingRunId": str(processing_run_id),
                "status": status,
                "progress": progress,
                "message": message,
            },
            timeout=httpx.Timeout(30.0, connect=15.0),
        )
        response.raise_for_status()
