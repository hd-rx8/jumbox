# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-08-18

### Added
- **Resumable Chunk Upload Protocol:** Interruption-safe chunk streaming (PATCH /chunks) with Upload-Offset probing that recovers from network drops without retransmitting bytes.
- **Automatic Retry Engine:** Bounded exponential backoff with full jitter on network drops (up to 5 attempts).
- **Ephemeral Transfers (Burn After Download):** Optional single-use mode where transfers automatically self-destruct and purge files from disk after recipient download.
- **Standalone Zero-Config Mode:** Native SQLite support with in-process background cleanup without requiring Redis or Celery.
- **Obsidian Flux Dark UI:** Modern developer-tool aesthetic with Glassmorphism, real-time speed/ETA metrics, and mobile QR code generation with automatic host LAN IP detection.
- **Manual Session Deletion:** Trash button and DELETE /api/v1/sessions/{id} endpoint for immediate session purging.

## [1.0.0] - 2026-08-18

### Added
- Multi-file transfer sessions with 8-digit share codes and QR codes.
- Per-item progress tracking and failure isolation.
- End-to-end SHA-256 integrity verification.
- Direct streaming downloads with Accept-Ranges: bytes support.
- Background session expiration and file cleanup routines.
- SQLAlchemy 2.0 and Alembic database migrations.
