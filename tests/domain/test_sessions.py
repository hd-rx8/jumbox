from uuid import uuid4
from app.domain.sessions import TransferSession, TransferItem, SessionStatus, ItemStatus

def test_transfer_session_aggregate_progress():
    session = TransferSession(owner_id=uuid4(), session_code="7431-9285")
    item1 = TransferItem(session_id=session.id, original_name="a.pdf", size_bytes=1000)
    item2 = TransferItem(session_id=session.id, original_name="b.mp4", size_bytes=2000)
    
    session.add_item(item1)
    session.add_item(item2)
    
    assert session.total_size_bytes == 3000
    assert session.status == SessionStatus.PENDING
    
    item1.mark_completed(checksum_sha256="abc123hash", storage_path="/path/a.pdf")
    assert item1.status == ItemStatus.COMPLETED
    assert session.status == SessionStatus.IN_PROGRESS
    
    item2.mark_completed(checksum_sha256="def456hash", storage_path="/path/b.mp4")
    assert session.status == SessionStatus.READY


def test_transfer_session_burn_after_download():
    session = TransferSession(
        owner_id=uuid4(),
        session_code="1111-2222",
        burn_after_download=True,
    )
    assert session.burn_after_download is True
    assert session.download_count == 0
    assert session.status == SessionStatus.PENDING

    session.record_download()
    assert session.download_count == 1
    assert session.status == SessionStatus.EXPIRED

