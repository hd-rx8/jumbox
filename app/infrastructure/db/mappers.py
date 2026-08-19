from __future__ import annotations

from app.domain.sessions import ItemStatus, SessionStatus, TransferItem, TransferSession
from app.domain.transfers import Folder, Transfer, TransferStatus
from app.infrastructure.db.models import (
    FolderModel,
    TransferItemModel,
    TransferModel,
    TransferSessionModel,
)


def transfer_to_domain(model: TransferModel) -> Transfer:
    return Transfer(
        id=model.id,
        owner_id=model.owner_id,
        folder_id=model.folder_id,
        original_name=model.original_name,
        stored_name=model.stored_name,
        storage_path=model.storage_path,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        transfer_code=model.transfer_code,
        status=TransferStatus(model.status),
        expires_at=model.expires_at,
        downloaded_at=model.downloaded_at,
        version_number=model.version_number,
        search_text=model.search_text,
        sha256_verified=model.sha256_verified,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def transfer_to_model(domain: Transfer) -> TransferModel:
    return TransferModel(
        id=domain.id,
        owner_id=domain.owner_id,
        folder_id=domain.folder_id,
        original_name=domain.original_name,
        stored_name=domain.stored_name,
        storage_path=domain.storage_path or "",
        size_bytes=domain.size_bytes,
        checksum_sha256=domain.checksum_sha256,
        transfer_code=domain.transfer_code,
        status=domain.status.value,
        expires_at=domain.expires_at,
        downloaded_at=domain.downloaded_at,
        version_number=domain.version_number,
        search_text=domain.search_text,
        sha256_verified=domain.sha256_verified,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def folder_to_domain(model: FolderModel) -> Folder:
    return Folder(
        id=model.id,
        owner_id=model.owner_id,
        parent_id=model.parent_id,
        name=model.name,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def folder_to_model(domain: Folder) -> FolderModel:
    return FolderModel(
        id=domain.id,
        owner_id=domain.owner_id,
        parent_id=domain.parent_id,
        name=domain.name,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def item_to_domain(model: TransferItemModel) -> TransferItem:
    return TransferItem(
        id=model.id,
        session_id=model.session_id,
        original_name=model.original_name,
        stored_name=model.stored_name,
        storage_path=model.storage_path,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        status=ItemStatus(model.status),
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def item_to_model(domain: TransferItem) -> TransferItemModel:
    return TransferItemModel(
        id=domain.id,
        session_id=domain.session_id,
        original_name=domain.original_name,
        stored_name=domain.stored_name,
        storage_path=domain.storage_path,
        size_bytes=domain.size_bytes,
        checksum_sha256=domain.checksum_sha256,
        status=domain.status.value,
        error_message=domain.error_message,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def session_to_domain(model: TransferSessionModel) -> TransferSession:
    items = [item_to_domain(item) for item in model.items] if model.items else []
    session = TransferSession(
        id=model.id,
        owner_id=model.owner_id,
        session_code=model.session_code,
        expires_at=model.expires_at,
        burn_after_download=model.burn_after_download,
        download_count=model.download_count,
        items=items,
        created_at=model.created_at,
        updated_at=model.updated_at,
        _status=SessionStatus(model.status),
    )
    return session


def session_to_model(domain: TransferSession) -> TransferSessionModel:
    return TransferSessionModel(
        id=domain.id,
        owner_id=domain.owner_id,
        session_code=domain.session_code,
        status=domain.status.value,
        expires_at=domain.expires_at,
        burn_after_download=domain.burn_after_download,
        download_count=domain.download_count,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )

