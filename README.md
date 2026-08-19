# Jumbox

> **Private, local-first file transfer system with multi-file sessions, resumable streaming, end-to-end SHA-256 integrity, and ephemeral single-use sharing.**

[![Tests](https://img.shields.io/badge/tests-19%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)

Jumbox is an open-source tool designed for fast, direct, and private file transfers across your local network (LAN/Wi-Fi). It turns any machine on your network into an instant sharing hub without sending your files to third-party cloud servers.

---

## 📸 Screenshots

<div align="center">
  <h3>🏠 Home Dashboard</h3>
  <img src="img-demo/print01.png" alt="Jumbox Home Dashboard" width="850" />

  <br/><br/>

  <h3>📤 Send Files & Share Credentials</h3>
  <img src="img-demo/print02.png" alt="Jumbox Send Files & QR Code" width="850" />

  <br/><br/>

  <h3>📋 Transfer Sessions Management</h3>
  <img src="img-demo/print03.png" alt="Jumbox Transfer Sessions" width="850" />

  <br/><br/>

  <h3>📥 Receive Files & Package Inspector</h3>
  <img src="img-demo/print04.png" alt="Jumbox Receive Files" width="850" />
</div>

---

## ✨ Features

- **Multi-File Transfer Sessions:** Send batches of files grouped under a clean 8-digit share code (e.g. `7431-9285`) or instant QR code for mobile scanning.
- **Resumable Chunk Transfers:** Interruption-safe chunk upload protocol (`PATCH .../chunks` with `Upload-Offset` probing) that recovers seamlessly from network drops without retransmitting already accepted bytes.
- **Automatic Retry with Exponential Backoff:** Built-in bounded retries (up to 5 attempts with jitter) for transient connection errors.
- **Per-Item State & Telemetry:** Track individual upload progress, real-time speed in **MB/s**, and estimated time remaining for each file.
- **End-to-End Integrity:** Automatic SHA-256 calculation with verification headers (`X-Checksum-SHA256` and `ETag`) to protect against corrupted transfers.
- **Direct Streaming Downloads:** Stream directly to the receiver's disk with `Accept-Ranges: bytes` support without memory buffer overflow.
- **Ephemeral Transfers (Burn After Download):** Optional single-use mode where transfers automatically self-destruct and purge files from disk as soon as the recipient downloads them.
- **Standalone Zero-Config Mode:** Native SQLite support with automatic startup schema creation and in-process background cleanup without requiring Redis or Celery.
- **Obsidian Flux Dark UI:** Modern developer-tool aesthetic with Glassmorphism, real-time speed/ETA metrics, and mobile QR code generation with automatic host LAN IP detection.
- **Session Management:** Instant manual cancellation/deletion with disk cleanup.

---

## 🏗️ Architecture

- **Domain Layer (`app/domain`):** `TransferSession` aggregate root managing collections of `TransferItem` entities with computed progress and failure isolation.
- **Application Layer (`app/application`):** `SessionService` and `ChunkStorage` for session lifecycles, atomic storage path allocation (`uploads/{session_id}/{item_id}_{safename}`), and SHA-256 verification.
- **Persistence Layer (`app/infrastructure`):** SQLAlchemy 2.0 with Alembic migrations, supporting both SQLite (standalone/development) and PostgreSQL (server/production).
- **Presentation Layer (`app/api` & `app/static`):** FastAPI REST endpoints at `/api/v1/sessions` and responsive dark-theme frontend at `/static`.

---

## 🚀 Quick Start

### 1. Python Standalone Mode (Zero-Config)

```bash
# Clone the repository
git clone https://github.com/hd-rx8/jumbox.git
cd jumbox

# Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt pytest httpx

# Start the server (SQLite tables are created automatically on startup)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the interface in your browser:
- Local machine: **`http://localhost:8000`**
- Other devices on LAN/Wi-Fi: **`http://<YOUR-LOCAL-IP>:8000`**

### 2. Running with Docker Compose (Production Stack)

```bash
docker compose up --build
```

---

## 🧪 Running Tests

Jumbox comes with a comprehensive automated test suite covering domain aggregates, resumable chunk protocols, integrity verification, and standalone execution:

```bash
pytest -v
```

---

## 🤝 Contributing

Contributions are welcome! Please check [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and setup instructions.

---

## 🔒 Security

For security advisories and reporting guidelines, please refer to [SECURITY.md](SECURITY.md).

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).

