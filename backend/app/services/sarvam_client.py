"""Sarvam AI client — Document Intelligence async pipeline + Translate."""

import asyncio
import io
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings

# Sarvam Document Intelligence has a hard 10-page limit per job.
_DI_PAGE_LIMIT = 10

# Poll interval and max wait for a DI job to reach Completed/Failed.
_POLL_INTERVAL_S = 5
_MAX_WAIT_S = 300


class SarvamClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        if not self.settings.sarvam_api_key:
            raise RuntimeError("SARVAM_API_KEY is required for Sarvam OCR and translation.")
        return {"api-subscription-key": self.settings.sarvam_api_key}

    def _json_headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Document Intelligence — 5-step async pipeline
    # ------------------------------------------------------------------

    async def _di_create_job(self, client: httpx.AsyncClient) -> str:
        """Step 1: Create a Document Intelligence job. Returns job_id."""
        payload = {"job_parameters": {"language": "en-IN", "output_format": "md"}}
        r = await client.post(
            self.settings.sarvam_document_intelligence_url,
            json=payload,
            headers=self._json_headers(),
        )
        r.raise_for_status()
        return r.json()["job_id"]

    async def _di_get_upload_url(
        self, client: httpx.AsyncClient, job_id: str, filename: str
    ) -> str:
        """Step 2: Get pre-signed upload URL for the PDF."""
        url = f"{self.settings.sarvam_document_intelligence_url}/{job_id}/upload-files"
        r = await client.post(url, json={"files": [filename]}, headers=self._json_headers())
        r.raise_for_status()
        data = r.json()
        upload_urls: dict = data.get("upload_urls", {})
        # The presigned URL is the value associated with the filename key.
        presigned = upload_urls.get(filename) or next(iter(upload_urls.values()), None)
        if not presigned:
            raise RuntimeError(f"Sarvam did not return an upload URL for '{filename}'. Response: {data}")
        return presigned

    async def _di_upload_file(
        self, client: httpx.AsyncClient, presigned_url: str, pdf_bytes: bytes
    ) -> None:
        """Step 3: PUT the PDF to the pre-signed Azure Blob URL (no auth header)."""
        r = await client.put(
            presigned_url,
            content=pdf_bytes,
            headers={"Content-Type": "application/pdf", "x-ms-blob-type": "BlockBlob"},
        )
        r.raise_for_status()

    async def _di_start_job(self, client: httpx.AsyncClient, job_id: str) -> None:
        """Step 4: Start processing."""
        url = f"{self.settings.sarvam_document_intelligence_url}/{job_id}/start"
        r = await client.post(url, json={}, headers=self._json_headers())
        r.raise_for_status()

    async def _di_poll_status(self, client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
        """Step 5: Poll status until Completed, PartiallyCompleted, or Failed."""
        status_url = f"{self.settings.sarvam_document_intelligence_url}/{job_id}/status"
        elapsed = 0
        while elapsed < _MAX_WAIT_S:
            r = await client.get(status_url, headers=self._json_headers())
            r.raise_for_status()
            data = r.json()
            state: str = data.get("job_state", "")
            if state in {"Completed", "PartiallyCompleted"}:
                return data
            if state == "Failed":
                raise RuntimeError(f"Sarvam DI job {job_id} failed: {data.get('error_message')}")
            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S
        raise RuntimeError(f"Sarvam DI job {job_id} did not complete within {_MAX_WAIT_S}s.")

    async def _di_get_download_url(self, client: httpx.AsyncClient, job_id: str) -> str:
        """Step 6: Get pre-signed download URL for the Markdown output."""
        url = f"{self.settings.sarvam_document_intelligence_url}/{job_id}/download-files"
        r = await client.post(url, json={}, headers=self._json_headers())
        r.raise_for_status()
        data = r.json()
        download_urls: dict = data.get("download_urls", {})
        # Find the markdown output file (ends with .md or output_format is md).
        for key, val in download_urls.items():
            file_url = val.get("file_url") if isinstance(val, dict) else val
            if file_url:
                return file_url
        raise RuntimeError(f"No download URLs found in Sarvam DI response: {data}")

    async def _di_download_content(self, client: httpx.AsyncClient, download_url: str) -> str:
        """Step 7: Fetch and decode the Markdown (or ZIP-of-MD) content."""
        r = await client.get(download_url)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "")
        if "zip" in content_type or download_url.endswith(".zip"):
            # Unzip and concatenate all markdown files.
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                parts: list[str] = []
                for name in sorted(zf.namelist()):
                    if name.endswith(".md") or name.endswith(".txt"):
                        parts.append(zf.read(name).decode("utf-8", errors="replace"))
            return "\n\n".join(parts)
        return r.text

    # ------------------------------------------------------------------
    # Public API — OCR a PDF file using Document Intelligence
    # ------------------------------------------------------------------

    async def ocr_pdf(self, pdf_path: Path) -> str:
        """
        Run Sarvam Document Intelligence on a PDF file and return the extracted
        text as a single Markdown string.

        For PDFs longer than 10 pages (the Sarvam per-job limit), the PDF is
        split into 10-page batches and the results are concatenated.
        """
        import fitz  # PyMuPDF — already in requirements

        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        if page_count <= _DI_PAGE_LIMIT:
            return await self._ocr_pdf_chunk(pdf_path.read_bytes(), pdf_path.name)

        # Split into 10-page chunks and process each separately.
        chunks: list[str] = []
        doc = fitz.open(pdf_path)
        for start in range(0, page_count, _DI_PAGE_LIMIT):
            sub_doc = fitz.open()  # empty doc
            end = min(start + _DI_PAGE_LIMIT, page_count)
            sub_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
            chunk_bytes = sub_doc.tobytes()
            sub_doc.close()
            chunk_filename = f"{pdf_path.stem}_pages_{start + 1}_{end}.pdf"
            chunks.append(await self._ocr_pdf_chunk(chunk_bytes, chunk_filename))
        doc.close()
        return "\n\n".join(chunks)

    async def _ocr_pdf_chunk(self, pdf_bytes: bytes, filename: str) -> str:
        """Run the full 5-step Document Intelligence pipeline for one chunk."""
        async with httpx.AsyncClient(timeout=120) as client:
            job_id = await self._di_create_job(client)
            presigned_upload_url = await self._di_get_upload_url(client, job_id, filename)
            await self._di_upload_file(client, presigned_upload_url, pdf_bytes)
            await self._di_start_job(client, job_id)
            await self._di_poll_status(client, job_id)
            download_url = await self._di_get_download_url(client, job_id)
            return await self._di_download_content(client, download_url)

    # ------------------------------------------------------------------
    # Public API — Translate (unchanged)
    # ------------------------------------------------------------------

    async def translate_to_kannada(self, text: str) -> str:
        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": "kn-IN",
            "mode": "formal",
            "model": "sarvam-translate:v1",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.settings.sarvam_translate_url, json=payload, headers=self._json_headers()
            )
            response.raise_for_status()
            data = response.json()
        return data.get("translated_text") or data.get("output") or ""

    # ------------------------------------------------------------------
    # Public API — Create DI Job (kept for live integration test)
    # ------------------------------------------------------------------

    async def create_document_intelligence_job(
        self, language: str = "en-IN", output_format: str = "md"
    ) -> dict[str, Any]:
        payload = {"job_parameters": {"language": language, "output_format": output_format}}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.settings.sarvam_document_intelligence_url,
                json=payload,
                headers=self._json_headers(),
            )
            response.raise_for_status()
            return response.json()
