from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID
from datetime import UTC, datetime

import segno
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path as APIPath, Request, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import get_current_user, get_session_service
from app.api.schemas.sessions import (
    ChunkUploadResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    InitResumableItemRequest,
    OffsetResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
    TransferItemResponse,
)
from app.application.exceptions import (
    ItemNotFoundError,
    PermissionDeniedError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.application.sessions_service import SessionService
from app.domain.auth import AuthenticatedUser
from app.domain.sessions import TransferSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_item_response(item) -> TransferItemResponse:
    return TransferItemResponse(
        item_id=item.id,
        session_id=item.session_id,
        original_name=item.original_name,
        size_bytes=item.size_bytes,
        checksum_sha256=item.checksum_sha256,
        status=item.status.value if hasattr(item.status, "value") else str(item.status),
        error_message=item.error_message,
    )


def _to_detail_response(session: TransferSession) -> SessionDetailResponse:
    return SessionDetailResponse(
        session_id=session.id,
        session_code=session.session_code,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        expires_at=session.expires_at,
        burn_after_download=session.burn_after_download,
        download_count=session.download_count,
        total_size_bytes=session.total_size_bytes,
        items=[_to_item_response(i) for i in session.items],
        created_at=session.created_at,
    )


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> CreateSessionResponse:
    session = await session_service.create_session(
        owner=current_user,
        expires_in_seconds=payload.expires_in_seconds,
        burn_after_download=payload.burn_after_download,
    )
    return CreateSessionResponse(
        session_id=session.id,
        session_code=session.session_code,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        expires_at=session.expires_at,
        burn_after_download=session.burn_after_download,
    )


@router.post("/{session_id}/items", response_model=TransferItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_session_item(
    session_id: UUID,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> TransferItemResponse:
    try:
        item = await session_service.upload_item(
            session_id=session_id,
            owner=current_user,
            filename=file.filename or "file",
            file_content=file,
            size_bytes=file.size or 0,
        )
        return _to_item_response(item)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SessionExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc


@router.post("/{session_id}/items/resumable", response_model=TransferItemResponse, status_code=status.HTTP_201_CREATED)
async def init_resumable_item(
    session_id: UUID,
    payload: InitResumableItemRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> TransferItemResponse:
    try:
        item = await session_service.init_resumable_item(
            session_id=session_id,
            owner=current_user,
            original_name=payload.original_name,
            total_size_bytes=payload.total_size_bytes,
            expected_sha256=payload.expected_sha256,
        )
        return _to_item_response(item)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SessionExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc


@router.get("/{session_id}/items/{item_id}/offset", response_model=OffsetResponse)
async def get_item_offset(
    session_id: UUID,
    item_id: UUID,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> OffsetResponse:
    try:
        item, offset = await session_service.get_item_offset(session_id, item_id, owner=current_user)
        response.headers["Upload-Offset"] = str(offset)
        return OffsetResponse(
            item_id=item.id,
            bytes_received=offset,
            total_size_bytes=item.size_bytes,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/{session_id}/items/{item_id}/chunks", response_model=ChunkUploadResponse)
async def upload_item_chunk(
    session_id: UUID,
    item_id: UUID,
    request: Request,
    response: Response,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> ChunkUploadResponse:
    # Extract upload offset from headers
    raw_offset = request.headers.get("Upload-Offset")
    if raw_offset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Upload-Offset header")
    try:
        offset = int(raw_offset)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Upload-Offset header")

    chunk_data = await request.body()

    try:
        item, new_offset, completed = await session_service.append_item_chunk(
            session_id=session_id,
            item_id=item_id,
            owner=current_user,
            chunk_data=chunk_data,
            offset=offset,
        )
        response.headers["Upload-Offset"] = str(new_offset)
        return ChunkUploadResponse(
            item_id=item.id,
            bytes_received=new_offset,
            total_size_bytes=item.size_bytes,
            completed=completed,
            checksum_sha256=item.checksum_sha256 if completed else None,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SessionExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except ValueError as exc:
        err_msg = str(exc)
        if "Offset mismatch" in err_msg:
            # Query actual current offset
            _, current_offset = await session_service.get_item_offset(session_id, item_id, owner=current_user)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=err_msg,
                headers={"Upload-Offset": str(current_offset)},
            ) from exc
        if "Checksum mismatch" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg) from exc


@router.get("/mine", response_model=list[SessionSummaryResponse])
async def list_my_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionSummaryResponse]:
    sessions = await session_service.list_my_sessions(owner=current_user)
    return [
        SessionSummaryResponse(
            session_id=s.id,
            session_code=s.session_code,
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            expires_at=s.expires_at,
            burn_after_download=s.burn_after_download,
            download_count=s.download_count,
            total_size_bytes=s.total_size_bytes,
            item_count=len(s.items),
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get(
    "/{session_code}",
    response_model=SessionDetailResponse,
    summary="Get transfer session details by code",
    description="Public endpoint to inspect available files in an active transfer session using the share code.",
    responses={
        404: {"description": "Session not found"},
        410: {"description": "Session expired"},
    },
)
async def get_session(
    session_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    session_service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    session = await session_service.get_session_by_code(session_code)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return _to_detail_response(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete transfer session",
    description="Protected endpoint allowing the session owner to permanently remove a transfer session.",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Permission denied (not session owner)"},
        404: {"description": "Session not found"},
    },
)
async def delete_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> None:
    try:
        await session_service.delete_session(session_id, current_user)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc



@router.get(
    "/{session_code}/items/{item_id}/download",
    summary="Download file item from session",
    description="Public streaming download for a shared file within an active transfer session.",
    responses={
        404: {"description": "Item or file not found"},
    },
)
async def download_session_item(
    session_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    item_id: UUID = APIPath(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session_service: SessionService = Depends(get_session_service),
) -> FileResponse:
    result = await session_service.get_session_item(session_code, item_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in session")
    
    session, item = result
    if not item.storage_path or not Path(item.storage_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File missing on disk")

    if session.burn_after_download:
        background_tasks.add_task(session_service.burn_session, session.id)

    headers = {
        "Accept-Ranges": "bytes",
    }
    if item.checksum_sha256:
        headers["ETag"] = f'"{item.checksum_sha256}"'
        headers["X-Checksum-SHA256"] = item.checksum_sha256

    return FileResponse(
        path=Path(item.storage_path),
        filename=item.original_name,
        media_type="application/octet-stream",
        headers=headers,
    )



import socket
from urllib.parse import urlparse, urlunparse


def _get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.get(
    "/{session_code}/qr.png",
    summary="Generate QR code image for session",
    description="Public endpoint generating a high-precision QR code for LAN devices to join the transfer.",
    responses={
        404: {"description": "Session not found"},
    },
)
async def session_qr_png(
    session_code: str = APIPath(..., min_length=4, max_length=20, pattern=r"^[A-Za-z0-9-]+$"),
    request: Request = None,
    base_url: str | None = None,
    session_service: SessionService = Depends(get_session_service),
) -> Response:
    session = await session_service.get_session_by_code(session_code)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    resolved_base = base_url.rstrip("/") if base_url else str(request.base_url).rstrip("/")
    parsed = urlparse(resolved_base)
    # If the origin hostname is localhost or loopback, replace with LAN IP so mobile QR readers can connect
    if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
        lan_ip = _get_lan_ip()
        if lan_ip not in ("127.0.0.1", "localhost"):
            port_suffix = f":{parsed.port}" if parsed.port else ""
            netloc = f"{lan_ip}{port_suffix}"
            resolved_base = urlunparse((parsed.scheme or "http", netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)).rstrip("/")

    session_url = f"{resolved_base}/s/{session_code}"

    qr = segno.make(session_url)
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=6)

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
