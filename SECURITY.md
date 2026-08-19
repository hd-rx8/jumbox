# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Jumbox seriously. If you believe you have found a security vulnerability in Jumbox, please report it responsibly:

- **Do NOT** open a public GitHub issue for sensitive security vulnerabilities.
- Please email the maintainers or open a private GitHub Security Advisory.
- Include a detailed description of the issue, steps to reproduce, and potential impact.

## Local-First Threat Model & Best Practices

Jumbox is designed as a **local-first transfer system** intended for fast, private transfers across local networks (Wi-Fi/LAN) or privately routed connections.

### Endpoint Security Classification

1. **Intentionally Public Endpoints**:
   - `GET /health`: Load balancer and container orchestrator health probe. Exposes zero user or transfer data.
   - `POST /api/v1/auth/login` & `POST /api/v1/auth/register`: Authentication entry points. Protected by rate limiting.
   - `GET /api/v1/sessions/{session_code}` & `GET /api/v1/sessions/{session_code}/items/{item_id}/download`: Anonymous recipient handoff by 8-digit share code. Protected by rate limiting, expiration windows, and optional single-use Burn-After-Download.
   - UI Routes (`/`, `/upload`, `/download`, `/files`, `/s/{code}`): Static HTML/CSS/JS shell with Content Security Policy (CSP).

2. **Protected Endpoints (Require Bearer JWT)**:
   - User Profile: `GET /api/v1/auth/me`
   - Session & Transfer Creation: `POST /api/v1/sessions`, `POST /api/v1/transfers`, `POST /api/v1/uploads/sessions`
   - Resumable Chunk Streaming: `PATCH /api/v1/sessions/{id}/items/{id}/chunks`, `GET /api/v1/sessions/{id}/items/{id}/offset`
   - Transfer Management & Deletion: `DELETE /api/v1/sessions/{id}`, `GET /api/v1/sessions/mine`, `GET /api/v1/transfers/mine`
   - Folder Management: `POST /api/v1/folders`, `GET /api/v1/folders`

### Cryptographic Controls & Protections

- **Password Hashing**: PBKDF2 with SHA-256 and unique per-user salt.
- **Token Signature**: HMAC-SHA256 JWT tokens.
- **Content Integrity**: Rolling SHA-256 verification on all streaming uploads and downloads.
- **Random Number Generation**: Web Crypto API (`crypto.getRandomValues`) for frontend random seeds and Python `secrets` on backend.
- **HTTP Security Headers**: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`.

## GitGuard Scan Triage

Automated static scanners flag any route lacking an obvious auth decorator and any use of `innerHTML`, regardless of context. Jumbox uses FastAPI dependency injection (`Depends(get_current_user)`) and manual HTML escaping, patterns the scanner does not recognize, which produces a high false-positive rate. Each finding class from the GitGuard report was manually reviewed against the code:

| Finding class | Verdict | Notes |
| --- | --- | --- |
| "Missing Authentication" on `auth.py` (`/register`, `/login`), `health.py` (`/health`) | False positive | Intentionally public by design; see classification above. |
| "Missing Authentication" on `sessions.py`, `transfers.py`, `folders.py`, `uploads.py`, `search.py` (mutating/owner-scoped routes) | False positive | Already guarded by `Depends(get_current_user)`; scanner does not detect FastAPI DI as auth. |
| "Missing Authentication" on public share-code lookup/download/QR routes (`GET .../{code}`, `.../download`, `.../qr.png`) | False positive | Core product design — recipients authenticate by possessing the 8-digit share code, protected by rate limiting, expiration, and Burn-After-Download. |
| "Missing Authentication" on `pages.py` UI routes (`/`, `/upload`, `/download`, `/s/{code}`, `/files`) | False positive | Static HTML shell; no sensitive data is rendered server-side, all data fetched client-side through the already-protected API. |
| "XSS - Script Tag in User Input" (`pages.py:150`) | False positive | Flagged line is the static `<script src="/static/app.js">` tag, not user input. |
| "XSS - innerHTML Assignment" (`app.js`) | False positive | All dynamic values are passed through `escapeHtml()` before insertion; CSP additionally restricts `script-src 'self'`. |
| "Missing Authentication" on `GET /sessions/{session_id}/items/{item_id}/offset` | **Confirmed, fixed** | Endpoint queried resumable-upload progress without verifying the caller owned the session, unlike its sibling `PATCH .../chunks`. Now requires `Depends(get_current_user)` and checks `session.owner_id` (or admin) before returning data. |

Only the offset endpoint represented a real authorization gap; it has been fixed in `app/application/sessions_service.py` and `app/api/routes/sessions.py`.

