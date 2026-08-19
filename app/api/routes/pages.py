from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


ui_router = APIRouter(tags=["ui"])


def _layout(title: str, page: str, content: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en" class="dark">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#0b0e11" />
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&family=Silkscreen:wght@400;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/static/app.css" />
    <link rel="icon" type="image/png" href="/static/logo.png">
</head>
<body data-page="{page}">
    <!-- Background Ambient Effects & Tech Grid -->
    <div class="ambient-bg" aria-hidden="true">
        <div class="glow-orb glow-primary"></div>
        <div class="glow-orb glow-secondary"></div>
        <div class="tech-grid"></div>
    </div>

    <div class="app-shell">
        <header class="topbar">
            <div class="topbar-inner">
                <a class="brand" href="/">
                    <img src="/static/logo.png" alt="Jumbox Logo" class="brand-logo" width="30" height="30" />
                    <span class="brand-text">JUMBOX</span>
                    <span class="brand-tag">v1</span>
                </a>

                <nav class="nav-links">
                    <a href="/" class="nav-item" data-nav="home">Home</a>
                    <a href="/upload" class="nav-item" data-nav="upload">Send Files</a>
                    <a href="/files" class="nav-item" data-nav="files">Transfers</a>
                    <a href="/download" class="nav-item" data-nav="download">Receive</a>
                </nav>

                <div class="auth-panel" id="authPanel">
                    <div class="auth-status" id="authStatus">Not signed in</div>
                    <form class="auth-form" id="authForm">
                        <input type="email" name="email" placeholder="Email" autocomplete="email" required />
                        <input type="password" name="password" placeholder="Password" autocomplete="current-password" minlength="8" required />
                        <button type="submit" class="btn btn-secondary btn-sm">Sign in</button>
                        <button type="button" class="btn btn-ghost btn-sm" id="registerButton">Register</button>
                    </form>
                    <!-- Mobile Auth Toggle Button -->
                    <button type="button" class="mobile-auth-toggle-btn" id="mobileAuthToggle" aria-label="Account Settings">
                        <span class="material-symbols-outlined">account_circle</span>
                    </button>
                </div>
            </div>

            <!-- Mobile Auth Collapsible Drawer -->
            <div class="mobile-auth-drawer" id="mobileAuthDrawer" hidden>
                <div class="mobile-auth-drawer-inner">
                    <div class="mobile-auth-header">
                        <span class="mobile-auth-title" id="mobileAuthHeaderTitle">Account Access</span>
                        <button type="button" class="btn-drawer-close" id="mobileAuthClose" aria-label="Close">
                            <span class="material-symbols-outlined">close</span>
                        </button>
                    </div>
                    <form class="mobile-auth-form" id="mobileAuthForm">
                        <input type="email" name="email" placeholder="Email address" autocomplete="email" required />
                        <input type="password" name="password" placeholder="Password (min 8 chars)" autocomplete="current-password" minlength="8" required />
                        <div class="mobile-auth-actions">
                            <button type="submit" class="btn btn-primary btn-sm btn-wide">Sign in</button>
                            <button type="button" class="btn btn-ghost btn-sm btn-wide" id="mobileRegisterButton">Register</button>
                        </div>
                    </form>
                    <div id="mobileSignedInWrap" class="mobile-signed-in-wrap" hidden>
                        <span id="mobileUserEmail" class="mobile-user-email"></span>
                        <button type="button" id="mobileSignOutBtn" class="btn btn-ghost btn-sm btn-wide">Sign out</button>
                    </div>
                </div>
            </div>
        </header>

        <main class="page-main" data-page="{page}">
            {content}
        </main>

        <footer class="footer">
            <div class="footer-inner">
                <div class="footer-copy">
                    <span><strong>JUMBOX</strong> — Private local-first file transfers with SHA-256 integrity.</span>
                </div>
                <div class="footer-links">
                    <a href="https://github.com/hd-rx8/jumbox" target="_blank" rel="noopener">GitHub</a>
                    <a href="/docs" target="_blank">API Docs</a>
                </div>
            </div>
        </footer>
    </div>

    <!-- Mobile Bottom Navigation Bar -->
    <nav class="mobile-bottom-nav" aria-label="Mobile Navigation">
        <div class="mobile-bottom-nav-inner">
            <a href="/" class="mobile-nav-item" data-nav="home">
                <span class="material-symbols-outlined">home</span>
                <span>Home</span>
            </a>
            <a href="/upload" class="mobile-nav-item" data-nav="upload">
                <span class="material-symbols-outlined">cloud_upload</span>
                <span>Send</span>
            </a>
            <a href="/download" class="mobile-nav-item" data-nav="download">
                <span class="material-symbols-outlined">download</span>
                <span>Receive</span>
            </a>
            <a href="/files" class="mobile-nav-item" data-nav="files">
                <span class="material-symbols-outlined">swap_vert</span>
                <span>Transfers</span>
            </a>
        </div>
    </nav>
    <div class="mobile-nav-spacer" aria-hidden="true"></div>

    <div id="toastHost" class="toast-host"></div>
    <script src="/static/app.js" defer></script>
</body>
</html>"""
    return HTMLResponse(html)


@ui_router.get("/", response_class=HTMLResponse)
async def home_page() -> HTMLResponse:
    content = """
    <!-- Hero Section -->
    <section class="hero-bento reveal">
        <div class="hero-header">
            <div class="hero-badge">
                <span class="pulse-dot"></span>
                <span>LOCAL-FIRST TRANSFER NETWORK</span>
            </div>
            <h1 class="hero-title">
                Fast, private multi-file transfers
            </h1>
            <p class="hero-subtitle">
                Stream files directly between devices across your Wi-Fi or LAN with end-to-end SHA-256 integrity. No cloud uploads, no file size limits.
            </p>
        </div>

        <!-- Bento Action Cards -->
        <div class="bento-grid">
            <!-- Send Card -->
            <a href="/upload" class="bento-card bento-send group">
                <div class="bento-accent-bar accent-blue"></div>
                <div class="bento-icon-box icon-blue">
                    <span class="material-symbols-outlined">upload</span>
                </div>
                <h2 class="bento-title">Send Files</h2>
                <p class="bento-desc">Drop multiple files or folders to generate an instant 8-digit share code or QR code.</p>
                <div class="bento-action">
                    <span class="btn btn-primary btn-wide">
                        SELECT FILES
                        <span class="material-symbols-outlined icon-sm">arrow_forward</span>
                    </span>
                </div>
            </a>

            <!-- Receive Card -->
            <div class="bento-card bento-receive group">
                <div class="bento-accent-bar accent-cyan"></div>
                <div class="bento-icon-box icon-cyan">
                    <span class="material-symbols-outlined">download</span>
                </div>
                <h2 class="bento-title">Receive Files</h2>
                <p class="bento-desc">Enter an 8-digit code or scan a QR code to download files directly to your device.</p>
                <form action="/download" method="get" class="quick-code-form">
                    <input class="quick-code-input" name="code" placeholder="Enter code (e.g. 7431-9285)..." type="text" maxlength="9" />
                    <button type="submit" class="btn btn-secondary">
                        <span class="material-symbols-outlined">arrow_forward</span>
                    </button>
                </form>
            </div>
        </div>
    </section>

    <!-- 3-Step Feature Guide -->
    <section class="flow-steps reveal delay-1">
        <div class="step-card">
            <div class="step-icon-wrap">
                <span class="material-symbols-outlined step-icon text-blue">touch_app</span>
            </div>
            <div class="step-meta">01. SELECT</div>
            <h3>Queue Multiple Files</h3>
            <p>Select any batch of files. Jumbox handles resilient chunked streaming without RAM overflow.</p>
        </div>
        <div class="step-card">
            <div class="step-icon-wrap">
                <span class="material-symbols-outlined step-icon text-cyan">share</span>
            </div>
            <div class="step-meta">02. SHARE</div>
            <h3>8-Digit Code & QR</h3>
            <p>Instant formatted transfer code and high-precision QR code automatically routed to your LAN IP.</p>
        </div>
        <div class="step-card">
            <div class="step-icon-wrap">
                <span class="material-symbols-outlined step-icon text-red">verified</span>
            </div>
            <div class="step-meta">03. VERIFY</div>
            <h3>Stream & Auto-Destruct</h3>
            <p>Streaming downloads with rolling SHA-256 validation and optional single-use Burn-After-Download.</p>
        </div>
    </section>
    """
    return _layout("Jumbox - Fast, Private File Transfers", "home", content)


@ui_router.get("/upload", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    content = """
    <section class="page-header reveal">
        <div>
            <div class="page-tag">TRANSFER SESSION</div>
            <h1 class="page-title">Send files to another device</h1>
            <p class="page-desc">
                Queue one or multiple files to create an active transfer session. Share the 8-digit code or scan the QR code from the receiving device.
            </p>
        </div>
    </section>

    <section class="transfer-layout">
        <!-- Left: Upload Configuration & Dropzone -->
        <article class="glass-panel upload-panel reveal">
            <form id="uploadSessionForm" class="upload-form">
                <div id="dropZone" class="dropzone" tabindex="0">
                    <input id="uploadFiles" name="files" type="file" multiple hidden />
                    <div class="dropzone-content">
                        <div class="dropzone-icon">
                            <span class="material-symbols-outlined">cloud_upload</span>
                        </div>
                        <h2 class="dropzone-heading">Drop files here to send</h2>
                        <p class="dropzone-sub">or <span class="browse-link">click to browse</span> from your device</p>
                        <div class="dropzone-badges">
                            <span class="tech-chip">Multi-file support</span>
                            <span class="tech-chip">Resumable chunks</span>
                            <span class="tech-chip">SHA-256 verified</span>
                        </div>
                    </div>
                </div>

                <!-- Selected files queue list -->
                <div id="selectedFilesQueue" class="file-queue-panel" hidden>
                    <div class="file-queue-header">
                        <span class="queue-title">Files in Queue (<span id="queueCount">0</span>)</span>
                        <span id="queueTotalSize" class="queue-size-badge">0 MB</span>
                    </div>
                    <div id="queueList" class="file-queue-items"></div>
                </div>

                <!-- Session Options -->
                <div class="session-options-grid">
                    <label class="control-field">
                        <span class="control-label">Session Availability</span>
                        <select id="sessionExpiresIn" class="select-input">
                            <option value="1800">30 minutes</option>
                            <option value="3600" selected>1 hour</option>
                            <option value="21600">6 hours</option>
                            <option value="86400">24 hours</option>
                        </select>
                    </label>

                    <label class="checkbox-control">
                        <input type="checkbox" id="sessionBurnAfterDownload" />
                        <span class="checkbox-label">
                            <strong>🔥 Burn after download</strong>
                            <small>Auto-destruir e apagar arquivos após 1º download</small>
                        </span>
                    </label>
                </div>

                <button type="submit" id="startUploadBtn" class="btn btn-primary btn-lg btn-wide" disabled>
                    <span class="material-symbols-outlined icon-sm">bolt</span>
                    Start Transfer
                </button>

                <!-- Real-time Progress Bar -->
                <div id="sessionProgressWrap" class="progress-container" hidden>
                    <div class="progress-header">
                        <span id="sessionProgressStatus" class="progress-status-text">Transferring files...</span>
                        <strong id="sessionProgressPercent" class="progress-percent">0%</strong>
                    </div>
                    <div class="progress-track">
                        <div id="sessionProgressBar" class="progress-bar-fill" style="width: 0%"></div>
                    </div>
                    <div class="progress-telemetry">
                        <span id="sessionUploadSpeed" class="telemetry-item">0 MB/s</span>
                        <span id="sessionTimeRemaining" class="telemetry-item">Calculating...</span>
                    </div>
                </div>
            </form>
        </article>

        <!-- Right: Transfer Result & QR Handoff -->
        <article class="glass-panel result-panel reveal delay-1" id="sessionResultCard">
            <div class="result-header">
                <span class="page-tag">SHARE CREDENTIALS</span>
                <h2 class="result-title">Transfer Code & QR</h2>
                <p id="sessionResultHint" class="result-hint">Your 8-digit transfer code and QR code will appear here once the transfer starts.</p>
            </div>

            <!-- 8-Digit Code Display -->
            <div class="code-showcase">
                <div class="code-digits" id="sessionCodeDisplay">---- - ----</div>
                <button type="button" class="btn btn-secondary btn-sm" id="copySessionCodeBtn" disabled>
                    <span class="material-symbols-outlined icon-sm">content_copy</span>
                    Copy Code
                </button>
            </div>

            <!-- QR Code Box -->
            <div class="qr-showcase">
                <div class="qr-frame">
                    <img id="sessionQrCode" alt="Transfer QR Code" class="qr-image" style="display: none;" />
                    <div id="qrPlaceholder" class="qr-placeholder">
                        <span class="material-symbols-outlined qr-icon">qr_code_2</span>
                        <span class="qr-placeholder-text">Scan with camera on local Wi-Fi</span>
                    </div>
                </div>
            </div>

            <div class="result-actions">
                <a class="btn btn-ghost btn-wide" id="sessionShareLink" href="#" target="_blank" style="display: none;">
                    <span class="material-symbols-outlined icon-sm">open_in_new</span>
                    Open Transfer Page
                </a>
            </div>
        </article>
    </section>
    """
    return _layout("Jumbox - Send Files", "upload", content)


@ui_router.get("/download", response_class=HTMLResponse)
@ui_router.get("/receive", response_class=HTMLResponse)
async def receive_page() -> HTMLResponse:
    content = """
    <section class="page-header reveal">
        <div>
            <div class="page-tag">RECEIVE FILES</div>
            <h1 class="page-title">Download transfer bundle</h1>
            <p class="page-desc">
                Enter the 8-digit transfer code (e.g. 7431-9285) to inspect and download all files shared in the session.
            </p>
        </div>
    </section>

    <section class="receive-layout">
        <!-- Left: 8-Bit Cyber Code Input Card -->
        <article class="glass-panel lookup-panel cyber-receiver-card reveal">
            <div class="result-header">
                <span class="page-tag">ENCRYPTED CHANNEL</span>
                <h2 class="result-title">Access Bundle</h2>
                <p class="result-hint">Enter the 8-digit key to unlock files directly from the sender.</p>
            </div>

            <form id="receiveCodeForm" class="lookup-form">
                <div class="code-matrix-display">
                    <div class="matrix-scanline"></div>
                    <div class="matrix-header">
                        <span class="matrix-status-dot"></span>
                        <span class="matrix-status-text">SYSTEM READY // ENTER KEY</span>
                    </div>

                    <div class="code-input-wrapper">
                        <input
                            id="receiveCodeInput"
                            type="text"
                            class="code-text-input-8bit"
                            maxlength="9"
                            placeholder="____-____"
                            autocomplete="off"
                            required
                            spellcheck="false"
                            autofocus
                        />
                    </div>

                    <div class="matrix-corner top-left"></div>
                    <div class="matrix-corner top-right"></div>
                    <div class="matrix-corner bottom-left"></div>
                    <div class="matrix-corner bottom-right"></div>
                </div>

                <div class="lookup-actions">
                    <button type="submit" id="lookupSessionBtn" class="btn btn-primary btn-lg btn-wide btn-neon-cyan">
                        <span class="material-symbols-outlined icon-sm">lock_open</span>
                        DECRYPT & FETCH
                    </button>
                </div>
            </form>
        </article>

        <!-- Right: Session Inspector & Download -->
        <article class="glass-panel inspector-panel reveal delay-1" id="sessionItemsCard">
            <div class="result-header">
                <span class="page-tag">PACKAGE INSPECTOR</span>
                <h2 class="result-title">Session Details</h2>
                <p id="receiveSessionHint" class="result-hint">Enter a code on the left to load available files.</p>
            </div>

            <div id="receiveSessionContent" hidden>
                <div id="receiveBurnWarning" class="burn-warning-banner" hidden>
                    🔥 <strong>Burn-after-download session:</strong> This transfer is single-use. Files will be permanently deleted from the host immediately after download.
                </div>

                <div class="session-meta-bar">
                    <span class="status-chip chip-ready" id="receiveSessionStatus">Ready</span>
                    <span id="receiveSessionTotalSize" class="meta-size">0 MB total</span>
                    <span id="receiveSessionExpires" class="meta-exp">Expires in --</span>
                </div>

                <div id="receiveItemsList" class="receive-items-list"></div>

                <div class="receive-actions">
                    <button type="button" id="downloadAllBtn" class="btn btn-primary btn-lg btn-wide">
                        <span class="material-symbols-outlined icon-sm">download</span>
                        Download All Files
                    </button>
                </div>
            </div>
        </article>
    </section>
    """
    return _layout("Jumbox - Receive Files", "download", content)


@ui_router.get("/s/{session_code}", response_class=HTMLResponse)
async def direct_session_page(session_code: str) -> HTMLResponse:
    content = f"""
    <section class="page-header reveal">
        <div>
            <div class="page-tag">DIRECT TRANSFER</div>
            <h1 class="page-title">Session {session_code}</h1>
            <p class="page-desc">Files shared in this transfer session are ready for instant streaming download.</p>
        </div>
    </section>

    <section class="glass-panel direct-container reveal" id="directSessionContainer" data-code="{session_code}">
        <div class="result-header">
            <span class="page-tag">SESSION BUNDLE</span>
            <h2 class="result-title">Available Files</h2>
            <p id="directSessionHint" class="result-hint">Loading files for session {session_code}...</p>
        </div>

        <div id="directSessionContent" hidden>
            <div id="directBurnWarning" class="burn-warning-banner" hidden>
                🔥 <strong>Burn-after-download session:</strong> This transfer is single-use. Files will be permanently deleted immediately after download.
            </div>

            <div class="session-meta-bar">
                <span class="status-chip chip-ready" id="directSessionStatus">Ready</span>
                <span id="directSessionTotalSize" class="meta-size">0 MB</span>
                <span id="directSessionExpires" class="meta-exp">Expires in --</span>
            </div>

            <div id="directItemsList" class="receive-items-list"></div>

            <div class="receive-actions">
                <button type="button" id="directDownloadAllBtn" class="btn btn-primary btn-lg">
                    <span class="material-symbols-outlined icon-sm">download</span>
                    Download All Files
                </button>
            </div>
        </div>
    </section>
    """
    return _layout(f"Jumbox - Transfer {session_code}", "direct_session", content)


@ui_router.get("/files", response_class=HTMLResponse)
async def transfers_history_page() -> HTMLResponse:
    content = """
    <section class="page-header reveal">
        <div>
            <div class="page-tag">TRANSFER LOG</div>
            <h1 class="page-title">Your Transfer Sessions</h1>
            <p class="page-desc">
                Manage active and past transfers, copy share codes, monitor remaining availability, or delete sessions.
            </p>
        </div>
    </section>

    <section class="glass-panel history-panel reveal">
        <div class="history-header">
            <div>
                <h2 class="history-title">Recent Activity</h2>
                <p id="filesListHint" class="history-hint">Loading your transfer sessions...</p>
            </div>
            <div class="history-search">
                <input id="sessionsSearch" type="search" class="search-input" placeholder="Search by session code..." autocomplete="off" />
            </div>
        </div>

        <div id="sessionsList" class="sessions-list" aria-live="polite"></div>

        <div id="sessionsEmpty" class="files-empty" hidden>
            <div class="empty-icon-wrap">
                <span class="material-symbols-outlined empty-icon">folder_open</span>
            </div>
            <h2>No transfer sessions yet</h2>
            <p>Send files to create your first transfer session.</p>
            <a class="btn btn-primary" href="/upload">
                <span class="material-symbols-outlined icon-sm">upload</span>
                Send your first transfer
            </a>
        </div>
    </section>
    """
    return _layout("Jumbox - My Transfers", "files", content)
