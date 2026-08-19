from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as APIPath, UploadFile, status
from fastapi.responses import FileResponse
from fastapi import Request, Response
import segno

from app.api.dependencies import get_current_user, get_settings, get_uow
from app.api.schemas.transfers import TransferDownloadResponse, TransferUploadResponse
from app.application.exceptions import NotFoundError
from app.application.transfer_codes import TransferCodeGenerator
from app.application.transfers_service import TransferService
from app.application.uow import SQLAlchemyUnitOfWork
from app.core.settings import Settings
from app.domain.auth import AuthenticatedUser
from app.infrastructure.storage.local import LocalFileStorage


router = APIRouter(prefix="/transfers", tags=["transfers"])


def get_transfer_service(settings: Settings = Depends(get_settings), uow: SQLAlchemyUnitOfWork = Depends(get_uow)) -> TransferService:
    file_storage = LocalFileStorage(settings.uploads_dir)
    return TransferService(uow=uow, file_storage=file_storage, code_generator=TransferCodeGenerator())


@router.post(
    "",
    response_model=TransferUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload single transfer",
    description="Protected endpoint allowing authenticated users to upload and share a single file transfer.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def upload_transfer(
    file: UploadFile = File(...),
    expires_in_seconds: int | None = Form(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    transfer_service: TransferService = Depends(get_transfer_service),
) -> TransferUploadResponse:
    result = await transfer_service.upload_file(
        owner=current_user,
        uploaded_file=file,
        expires_in_seconds=expires_in_seconds,
    )
    return TransferUploadResponse(
        transfer_id=str(result.transfer_id),
        transfer_code=result.transfer_code,
        download_url=result.download_url,
        expires_at=result.expires_at,
        sha256=result.sha256,
        size_bytes=result.size_bytes,
        original_name=result.original_name,
    )

@router.get(
    "/mine",
    response_model=list[TransferDownloadResponse],
    summary="List user's transfers",
    description="Protected endpoint returning all file transfers uploaded by the authenticated user.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def list_my_transfers(
    current_user: AuthenticatedUser = Depends(get_current_user),
    transfer_service: TransferService = Depends(get_transfer_service),
) -> list[TransferDownloadResponse]:
    transfers = await transfer_service.list_for_owner(
        owner_id=current_user.user_id,
    )

    return [
        TransferDownloadResponse(
            transfer_id=str(transfer.id),
            transfer_code=transfer.transfer_code or "",
            original_name=transfer.original_name,
            size_bytes=transfer.size_bytes,
            sha256=transfer.checksum_sha256,
            status=transfer.status.value,
            expires_at=transfer.expires_at,
        )
        for transfer in transfers
    ]


@router.get(
    "/{transfer_code}",
    response_model=TransferDownloadResponse,
    summary="Get transfer metadata by code",
    description="Public endpoint to inspect metadata for a single transfer by its 8-digit share code.",
    responses={
        404: {"description": "Transfer not found"},
    },
)
async def get_transfer_metadata(
    transfer_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    transfer_service: TransferService = Depends(get_transfer_service),
) -> TransferDownloadResponse:
    try:
        transfer = await transfer_service.resolve_transfer(transfer_code)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TransferDownloadResponse(
        transfer_id=str(transfer.id),
        transfer_code=transfer.transfer_code or transfer_code,
        original_name=transfer.original_name,
        size_bytes=transfer.size_bytes,
        sha256=transfer.checksum_sha256,
        status=transfer.status.value,
        expires_at=transfer.expires_at,
    )


@router.get(
    "/{transfer_code}/download",
    summary="Download single transfer file",
    description="Public streaming download for a single transfer file using its share code.",
    responses={
        404: {"description": "Transfer or file not found"},
        410: {"description": "Transfer expired"},
    },
)
async def download_transfer(
    transfer_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    transfer_service: TransferService = Depends(get_transfer_service),
) -> FileResponse:
    try:
        transfer = await transfer_service.resolve_transfer(transfer_code)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if transfer.expires_at is not None and transfer.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Transfer has expired")

    await transfer_service.mark_downloaded(transfer_code)
    storage_path = Path(transfer.storage_path or "")
    if not storage_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        path=storage_path,
        filename=transfer.original_name,
        media_type="application/octet-stream",
    )


import io
@router.get(
    "/{transfer_code}/qr.png",
    summary="Generate QR code for single transfer",
    description="Public endpoint generating a QR code for direct download of the single transfer.",
    responses={
        404: {"description": "Transfer not found"},
        410: {"description": "Transfer expired"},
    },
)
async def transfer_qr_png(
    transfer_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    request: Request = None,
    transfer_service: TransferService = Depends(get_transfer_service),
) -> Response:
    try:
        transfer = await transfer_service.resolve_transfer(transfer_code)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if transfer.expires_at is not None and transfer.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Transfer has expired",
        )

    download_url = str(
        request.url_for(
            "download_transfer",
            transfer_code=transfer_code,
        )
    )

    qr = segno.make(download_url)

    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=6)

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
        },
    )