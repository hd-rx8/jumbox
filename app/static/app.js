const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'jumbox.access_token';

function $(id) {
    return document.getElementById(id);
}

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
    refreshAuthStatus();
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    refreshAuthStatus();
}

function decodeJwtPayload(token) {
    try {
        const payload = token.split('.')[1];
        const json = atob(payload.replaceAll('-', '+').replaceAll('_', '/'));
        return JSON.parse(decodeURIComponent(Array.from(json, c => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`).join('')));
    } catch {
        return null;
    }
}

function toast(message, kind = 'success') {
    const host = $('toastHost');
    if (!host) return;
    const node = document.createElement('div');
    node.className = `toast ${kind}`;
    node.textContent = message;
    host.appendChild(node);
    window.setTimeout(() => node.remove(), 4500);
}

function formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function getFileExtension(filename) {
    const parts = (filename || '').split('.');
    return parts.length > 1 ? parts.pop().toUpperCase().slice(0, 4) : 'FILE';
}

function formatSessionCode(code) {
    if (!code) return '';
    const clean = code.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
    if (clean.length === 8) {
        return `${clean.slice(0, 4)} - ${clean.slice(4)}`;
    }
    return code;
}

function formatExpiration(expiresAt) {
    if (!expiresAt) return { text: 'No expiration', className: 'session-badge' };
    const exp = new Date(expiresAt);
    const now = new Date();
    const diff = exp.getTime() - now.getTime();
    if (diff <= 0) return { text: 'Expired', className: 'session-badge expired' };
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    if (days > 0) return { text: `Expires in ${days}d`, className: 'session-badge' };
    if (hours > 0) return { text: `Expires in ${hours}h`, className: 'session-badge' };
    return { text: `Expires in ${Math.max(1, minutes)}m`, className: 'session-badge' };
}

function refreshAuthStatus() {
    const statusEl = $('authStatus');
    const authForm = $('authForm');
    const mobileToggle = $('mobileAuthToggle');
    const mobileDrawer = $('mobileAuthDrawer');
    const mobileAuthForm = $('mobileAuthForm');
    const mobileSignedInWrap = $('mobileSignedInWrap');
    const mobileUserEmail = $('mobileUserEmail');
    const mobileHeaderTitle = $('mobileAuthHeaderTitle');

    const token = getToken();
    const user = token ? decodeJwtPayload(token) : null;

    if (!user) {
        if (statusEl) {
            statusEl.textContent = 'Not signed in';
            statusEl.classList.remove('signed-in');
        }
        if (authForm) authForm.style.display = 'flex';
        if (mobileToggle) mobileToggle.classList.remove('signed-in');
        if (mobileAuthForm) mobileAuthForm.hidden = false;
        if (mobileSignedInWrap) mobileSignedInWrap.hidden = true;
        if (mobileHeaderTitle) mobileHeaderTitle.textContent = 'Account Access';
    } else {
        const userDisplay = user.email || 'User';
        if (statusEl) {
            statusEl.textContent = `Signed in as ${userDisplay}`;
            statusEl.classList.add('signed-in');
        }
        if (authForm) {
            authForm.innerHTML = `<button type="button" id="signOutBtn" class="btn btn-ghost btn-sm">Sign out</button>`;
            $('signOutBtn')?.addEventListener('click', () => {
                clearToken();
                toast('Signed out.');
                window.location.reload();
            });
        }
        if (mobileToggle) mobileToggle.classList.add('signed-in');
        if (mobileAuthForm) mobileAuthForm.hidden = true;
        if (mobileSignedInWrap) mobileSignedInWrap.hidden = false;
        if (mobileUserEmail) mobileUserEmail.textContent = userDisplay;
        if (mobileHeaderTitle) mobileHeaderTitle.textContent = 'Signed in';
    }
}

function bindAuthForm() {
    const form = $('authForm');
    const registerBtn = $('registerButton');

    const mobileToggle = $('mobileAuthToggle');
    const mobileDrawer = $('mobileAuthDrawer');
    const mobileClose = $('mobileAuthClose');
    const mobileForm = $('mobileAuthForm');
    const mobileRegisterBtn = $('mobileRegisterButton');
    const mobileSignOutBtn = $('mobileSignOutBtn');

    mobileToggle?.addEventListener('click', () => {
        if (!mobileDrawer) return;
        mobileDrawer.hidden = !mobileDrawer.hidden;
    });

    mobileClose?.addEventListener('click', () => {
        if (mobileDrawer) mobileDrawer.hidden = true;
    });

    mobileSignOutBtn?.addEventListener('click', () => {
        clearToken();
        toast('Signed out.');
        if (mobileDrawer) mobileDrawer.hidden = true;
        window.location.reload();
    });

    async function handleLogin(payload) {
        const resp = await fetch(`${API_PREFIX}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || 'Login failed');
        }
        const data = await resp.json();
        setToken(data.access_token);
        toast('Signed in successfully.');
        refreshAuthStatus();
        if (mobileDrawer) mobileDrawer.hidden = true;
    }

    async function handleRegister(payload) {
        if (!payload.email || !payload.password) {
            throw new Error('Please enter email and password.');
        }
        const resp = await fetch(`${API_PREFIX}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || 'Registration failed');
        }
        const data = await resp.json();
        setToken(data.access_token);
        toast('Account created and signed in.');
        refreshAuthStatus();
        if (mobileDrawer) mobileDrawer.hidden = true;
    }

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(form).entries());
        try {
            await handleLogin(payload);
        } catch (err) {
            toast(err.message, 'error');
        }
    });

    registerBtn?.addEventListener('click', async (e) => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(form).entries());
        try {
            await handleRegister(payload);
        } catch (err) {
            toast(err.message, 'error');
        }
    });

    mobileForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(mobileForm).entries());
        try {
            await handleLogin(payload);
        } catch (err) {
            toast(err.message, 'error');
        }
    });

    mobileRegisterBtn?.addEventListener('click', async (e) => {
        e.preventDefault();
        const payload = Object.fromEntries(new FormData(mobileForm).entries());
        try {
            await handleRegister(payload);
        } catch (err) {
            toast(err.message, 'error');
        }
    });
}

/* =========================================================
   RESUMABLE CHUNK UPLOAD ENGINE
========================================================= */
const CHUNK_SIZE = 4 * 1024 * 1024; // 4MB chunks
const MAX_RETRIES = 5;

async function uploadFileResumable(file, sessionId, token, onProgress, onItemStatus) {
    // 1. Initialize resumable upload
    const initResp = await fetch(`${API_PREFIX}/sessions/${sessionId}/items/resumable`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            original_name: file.name,
            total_size_bytes: file.size,
        })
    });

    if (!initResp.ok) {
        const err = await initResp.json().catch(() => ({}));
        throw new Error(err.detail || `Failed to initialize upload for ${file.name}`);
    }

    const initData = await initResp.json();
    const itemId = initData.item_id;

    if (file.size === 0) {
        if (onItemStatus) onItemStatus('✓ Ready', 'status-completed');
        return;
    }

    // 2. Query initial offset
    let offset = 0;
    const offsetResp = await fetch(`${API_PREFIX}/sessions/${sessionId}/items/${itemId}/offset`);
    if (offsetResp.ok) {
        const offsetData = await offsetResp.json();
        offset = offsetData.bytes_received || 0;
    }

    // 3. Upload chunk loop with retry & backoff
    while (offset < file.size) {
        const end = Math.min(offset + CHUNK_SIZE, file.size);
        const chunkBlob = file.slice(offset, end);

        let attempt = 0;
        let success = false;

        while (attempt < MAX_RETRIES && !success) {
            try {
                const patchResp = await fetch(`${API_PREFIX}/sessions/${sessionId}/items/${itemId}/chunks`, {
                    method: 'PATCH',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/octet-stream',
                        'Upload-Offset': offset.toString(),
                    },
                    body: chunkBlob
                });

                if (patchResp.ok) {
                    const chunkResult = await patchResp.json();
                    const delta = chunkResult.bytes_received - offset;
                    offset = chunkResult.bytes_received;
                    onProgress(delta);
                    success = true;
                    if (onItemStatus) onItemStatus('Uploading...', 'status-uploading');
                } else if (patchResp.status === 409) {
                    // Conflict / offset mismatch - re-probe offset
                    const offResp = await fetch(`${API_PREFIX}/sessions/${sessionId}/items/${itemId}/offset`);
                    if (offResp.ok) {
                        const offData = await offResp.json();
                        offset = offData.bytes_received || 0;
                        break;
                    }
                    throw new Error('Offset synchronization failed');
                } else if (patchResp.status >= 400 && patchResp.status < 500) {
                    const err = await patchResp.json().catch(() => ({}));
                    throw new Error(err.detail || `Upload rejected (${patchResp.status})`);
                } else {
                    throw new Error(`Server error (${patchResp.status})`);
                }
            } catch (err) {
                attempt++;
                if (attempt >= MAX_RETRIES) {
                    if (onItemStatus) onItemStatus('✗ Failed', 'status-failed');
                    throw new Error(`Upload failed for ${file.name} after ${MAX_RETRIES} attempts: ${err.message}`);
                }
                const delayMs = Math.min(16000, 1000 * Math.pow(2, attempt - 1)) + (Math.random() * 500);
                if (onItemStatus) onItemStatus(`Retrying (${attempt}/${MAX_RETRIES})...`, 'status-retrying');
                await new Promise(r => setTimeout(r, delayMs));
            }
        }
    }

    if (onItemStatus) onItemStatus('✓ Ready', 'status-completed');
}

/* =========================================================
   UPLOAD / SEND PAGE
========================================================= */
function setupUploadPage() {
    const form = $('uploadSessionForm');
    const dropZone = $('dropZone');
    const fileInput = $('uploadFiles');
    const queueWrap = $('selectedFilesQueue');
    const queueList = $('queueList');
    const queueCount = $('queueCount');
    const queueTotalSize = $('queueTotalSize');
    const startBtn = $('startUploadBtn');
    const expiresSelect = $('sessionExpiresIn');
    const burnCheckbox = $('sessionBurnAfterDownload');

    const progressWrap = $('sessionProgressWrap');
    const progressBar = $('sessionProgressBar');
    const progressPercent = $('sessionProgressPercent');
    const progressStatus = $('sessionProgressStatus');
    const uploadSpeed = $('sessionUploadSpeed');
    const timeRemaining = $('sessionTimeRemaining');

    const codeDisplay = $('sessionCodeDisplay');
    const copyBtn = $('copySessionCodeBtn');
    const qrImg = $('sessionQrCode');
    const qrPlaceholder = $('qrPlaceholder');
    const shareLink = $('sessionShareLink');
    const resultHint = $('sessionResultHint');

    if (!form || !dropZone || !fileInput) return;

    let selectedFiles = [];

    function updateQueueUI() {
        if (!selectedFiles.length) {
            queueWrap.hidden = true;
            startBtn.disabled = true;
            return;
        }
        queueWrap.hidden = false;
        startBtn.disabled = false;
        queueCount.textContent = selectedFiles.length;
        const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
        queueTotalSize.textContent = formatBytes(totalBytes);

        queueList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const ext = getFileExtension(file.name);
            const itemEl = document.createElement('div');
            itemEl.className = 'queue-item';
            itemEl.id = `queueItem_${index}`;
            itemEl.innerHTML = `
                <div class="file-icon-badge">${ext}</div>
                <div class="queue-item-info">
                    <span class="queue-item-name">${file.name}</span>
                    <span class="queue-item-sub">${formatBytes(file.size)}</span>
                </div>
                <div class="queue-item-status status-queued" id="itemStatus_${index}">Queued</div>
            `;
            queueList.appendChild(itemEl);
        });
    }

    dropZone.addEventListener('click', () => fileInput.click());
    ['dragenter', 'dragover'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
    });
    ['dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });
    dropZone.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        if (files.length) {
            selectedFiles = files;
            updateQueueUI();
            toast(`${files.length} file(s) added to transfer.`);
        }
    });
    fileInput.addEventListener('change', () => {
        const files = Array.from(fileInput.files);
        if (files.length) {
            selectedFiles = files;
            updateQueueUI();
            toast(`${files.length} file(s) added to transfer.`);
        }
    });

    copyBtn?.addEventListener('click', async () => {
        const rawCode = copyBtn.dataset.code;
        if (!rawCode) return;
        try {
            await navigator.clipboard.writeText(rawCode);
            const original = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            toast('Transfer code copied to clipboard.');
            setTimeout(() => { copyBtn.textContent = original; }, 1500);
        } catch {
            toast('Could not copy code.', 'error');
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!selectedFiles.length) {
            toast('Please select at least one file.', 'error');
            return;
        }

        const token = getToken();
        if (!token) {
            toast('Please sign in or register above to create a transfer.', 'error');
            return;
        }

        startBtn.disabled = true;
        progressWrap.hidden = false;
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStatus.textContent = 'Creating session...';

        try {
            // 1. Create Transfer Session
            const expiresSeconds = parseInt(expiresSelect.value, 10) || 3600;
            const burnAfterDownload = burnCheckbox ? burnCheckbox.checked : false;

            const sessionResp = await fetch(`${API_PREFIX}/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    expires_in_seconds: expiresSeconds,
                    burn_after_download: burnAfterDownload,
                })
            });

            if (!sessionResp.ok) {
                if (sessionResp.status === 401) {
                    clearToken();
                    throw new Error('Authentication expired. Please sign in again.');
                }
                const err = await sessionResp.json().catch(() => ({}));
                throw new Error(err.detail || 'Could not initialize session.');
            }

            const sessionData = await sessionResp.json();
            const sessionId = sessionData.session_id;
            const sessionCode = sessionData.session_code;

            // Update UI with Session Code & QR
            codeDisplay.textContent = formatSessionCode(sessionCode);
            copyBtn.disabled = false;
            copyBtn.dataset.code = sessionCode;
            qrPlaceholder.style.display = 'none';
            qrImg.style.display = 'block';
            const originParam = encodeURIComponent(window.location.origin);
            qrImg.src = `${API_PREFIX}/sessions/${sessionCode}/qr.png?base_url=${originParam}`;
            shareLink.style.display = 'inline-flex';
            shareLink.href = `/s/${sessionCode}`;
            resultHint.textContent = burnAfterDownload
                ? 'Transfer active (Burn-after-download)! Files will self-destruct once downloaded.'
                : 'Transfer active! Share this 8-digit code or scan the QR code.';

            // 2. Upload each file in the queue with chunked resumable engine
            const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
            let uploadedBytes = 0;
            const startTime = Date.now();

            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i];
                const itemStatusEl = $(`itemStatus_${i}`);
                if (itemStatusEl) {
                    itemStatusEl.textContent = 'Uploading...';
                    itemStatusEl.className = 'queue-item-status status-uploading';
                }

                progressStatus.textContent = `Uploading ${i + 1} of ${selectedFiles.length}: ${file.name}`;

                await uploadFileResumable(
                    file,
                    sessionId,
                    token,
                    (delta) => {
                        uploadedBytes += delta;
                        const overallPercent = totalBytes > 0
                            ? Math.min(100, Math.round((uploadedBytes / totalBytes) * 100))
                            : 100;
                        progressBar.style.width = `${overallPercent}%`;
                        progressPercent.textContent = `${overallPercent}%`;

                        const elapsedSec = (Date.now() - startTime) / 1000;
                        if (elapsedSec > 0.5 && uploadedBytes > 0) {
                            const speedBytesPerSec = uploadedBytes / elapsedSec;
                            uploadSpeed.textContent = `${(speedBytesPerSec / (1024 * 1024)).toFixed(2)} MB/s`;
                            const remainingBytes = Math.max(0, totalBytes - uploadedBytes);
                            const secLeft = Math.ceil(remainingBytes / speedBytesPerSec);
                            timeRemaining.textContent = secLeft > 0 ? `${secLeft}s remaining` : 'Completing...';
                        }
                    },
                    (statusText, statusClass) => {
                        if (itemStatusEl) {
                            itemStatusEl.textContent = statusText;
                            itemStatusEl.className = `queue-item-status ${statusClass}`;
                        }
                    }
                );
            }

            progressBar.style.width = '100%';
            progressPercent.textContent = '100%';
            progressStatus.textContent = '✓ All files transferred and verified!';
            uploadSpeed.textContent = 'Complete';
            timeRemaining.textContent = '';
            toast('Transfer complete! All files are ready.');
        } catch (err) {
            toast(err.message, 'error');
            progressStatus.textContent = `Error: ${err.message}`;
        } finally {
            startBtn.disabled = false;
        }
    });
}

/* =========================================================
   RECEIVE / DOWNLOAD PAGE
========================================================= */
function setupReceivePage() {
    const form = $('receiveCodeForm');
    const codeInput = $('receiveCodeInput');
    const contentWrap = $('receiveSessionContent');
    const hintEl = $('receiveSessionHint');
    const statusBadge = $('receiveSessionStatus');
    const totalSizeEl = $('receiveSessionTotalSize');
    const expiresEl = $('receiveSessionExpires');
    const itemsList = $('receiveItemsList');
    const downloadAllBtn = $('downloadAllBtn');
    const burnWarning = $('receiveBurnWarning');

    if (!form || !codeInput) return;

    let currentSession = null;

    async function loadSession(code) {
        const cleanCode = code.replace(/[^a-zA-Z0-9-]/g, '').trim();
        if (!cleanCode) return;

        hintEl.textContent = `Searching for session ${cleanCode}...`;
        contentWrap.hidden = true;

        try {
            const resp = await fetch(`${API_PREFIX}/sessions/${cleanCode}`);
            if (!resp.ok) {
                if (resp.status === 404) throw new Error('Transfer session not found. Check the code.');
                if (resp.status === 410) throw new Error('This transfer session has expired or was already downloaded.');
                throw new Error('Could not load transfer session.');
            }

            currentSession = await resp.json();
            hintEl.textContent = `Found session with ${currentSession.items.length} file(s).`;
            contentWrap.hidden = false;

            if (burnWarning) {
                burnWarning.hidden = !currentSession.burn_after_download;
            }

            statusBadge.textContent = currentSession.status.toUpperCase();
            totalSizeEl.textContent = `${formatBytes(currentSession.total_size_bytes)} total`;
            const exp = formatExpiration(currentSession.expires_at);
            expiresEl.textContent = exp.text;

            itemsList.innerHTML = '';
            currentSession.items.forEach(item => {
                const ext = getFileExtension(item.original_name);
                const card = document.createElement('div');
                card.className = 'receive-item-card';
                const shaShort = item.checksum_sha256 ? `${item.checksum_sha256.slice(0, 8)}...` : '';
                card.innerHTML = `
                    <div class="file-icon-badge">${ext}</div>
                    <div class="receive-item-info">
                        <h4>${item.original_name}</h4>
                        <div class="receive-item-meta">
                            <span>${formatBytes(item.size_bytes)}</span>
                            ${shaShort ? `<span class="sha-badge" title="SHA-256: ${item.checksum_sha256}">SHA: ${shaShort}</span>` : ''}
                        </div>
                    </div>
                    <a class="btn btn-secondary btn-sm" href="${API_PREFIX}/sessions/${currentSession.session_code}/items/${item.item_id}/download" download="${item.original_name}">
                        Download
                    </a>
                `;
                itemsList.appendChild(card);
            });
        } catch (err) {
            hintEl.textContent = err.message;
            toast(err.message, 'error');
        }
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        loadSession(codeInput.value);
    });

    downloadAllBtn?.addEventListener('click', () => {
        if (!currentSession || !currentSession.items.length) return;
        toast(`Downloading ${currentSession.items.length} file(s)...`);
        currentSession.items.forEach((item, idx) => {
            setTimeout(() => {
                const link = document.createElement('a');
                link.href = `${API_PREFIX}/sessions/${currentSession.session_code}/items/${item.item_id}/download`;
                link.download = item.original_name;
                document.body.appendChild(link);
                link.click();
                link.remove();
            }, idx * 350);
        });
    });
}

/* =========================================================
   DIRECT SESSION VIEW (/s/{session_code})
========================================================= */
function setupDirectSessionPage() {
    const container = $('directSessionContainer');
    if (!container) return;
    const sessionCode = container.dataset.code;
    const hintEl = $('directSessionHint');
    const contentWrap = $('directSessionContent');
    const statusBadge = $('directSessionStatus');
    const totalSizeEl = $('directSessionTotalSize');
    const expiresEl = $('directSessionExpires');
    const itemsList = $('directItemsList');
    const downloadAllBtn = $('directDownloadAllBtn');
    const burnWarning = $('directBurnWarning');

    let currentSession = null;

    async function loadDirectSession() {
        try {
            const resp = await fetch(`${API_PREFIX}/sessions/${sessionCode}`);
            if (!resp.ok) {
                if (resp.status === 404) throw new Error('Transfer session not found.');
                if (resp.status === 410) throw new Error('This transfer session has expired or was already downloaded.');
                throw new Error('Failed to load session details.');
            }
            currentSession = await resp.json();
            hintEl.textContent = `${currentSession.items.length} file(s) available for download.`;
            contentWrap.hidden = false;

            if (burnWarning) {
                burnWarning.hidden = !currentSession.burn_after_download;
            }

            statusBadge.textContent = currentSession.status.toUpperCase();
            totalSizeEl.textContent = formatBytes(currentSession.total_size_bytes);
            const exp = formatExpiration(currentSession.expires_at);
            expiresEl.textContent = exp.text;

            itemsList.innerHTML = '';
            currentSession.items.forEach(item => {
                const ext = getFileExtension(item.original_name);
                const card = document.createElement('div');
                card.className = 'receive-item-card';
                const shaShort = item.checksum_sha256 ? `${item.checksum_sha256.slice(0, 8)}...` : '';
                card.innerHTML = `
                    <div class="file-icon-badge">${ext}</div>
                    <div class="receive-item-info">
                        <h4>${item.original_name}</h4>
                        <div class="receive-item-meta">
                            <span>${formatBytes(item.size_bytes)}</span>
                            ${shaShort ? `<span class="sha-badge" title="SHA-256: ${item.checksum_sha256}">SHA: ${shaShort}</span>` : ''}
                        </div>
                    </div>
                    <a class="btn btn-secondary btn-sm" href="${API_PREFIX}/sessions/${currentSession.session_code}/items/${item.item_id}/download" download="${item.original_name}">
                        Download
                    </a>
                `;
                itemsList.appendChild(card);
            });
        } catch (err) {
            hintEl.textContent = err.message;
            toast(err.message, 'error');
        }
    }

    downloadAllBtn?.addEventListener('click', () => {
        if (!currentSession || !currentSession.items.length) return;
        toast(`Downloading ${currentSession.items.length} file(s)...`);
        currentSession.items.forEach((item, idx) => {
            setTimeout(() => {
                const link = document.createElement('a');
                link.href = `${API_PREFIX}/sessions/${currentSession.session_code}/items/${item.item_id}/download`;
                link.download = item.original_name;
                document.body.appendChild(link);
                link.click();
                link.remove();
            }, idx * 350);
        });
    });

    loadDirectSession();
}

/* =========================================================
   MY TRANSFERS (HISTORY) PAGE
========================================================= */
function setupHistoryPage() {
    const listEl = $('sessionsList');
    const emptyEl = $('sessionsEmpty');
    const hintEl = $('filesListHint');
    const searchInput = $('sessionsSearch');

    if (!listEl) return;

    let sessions = [];

    function renderSessions(data) {
        listEl.innerHTML = '';
        if (!data.length) {
            listEl.hidden = true;
            emptyEl.hidden = false;
            hintEl.textContent = 'No transfer sessions found.';
            return;
        }
        listEl.hidden = false;
        emptyEl.hidden = true;
        hintEl.textContent = `${data.length} session${data.length === 1 ? '' : 's'}`;

        data.forEach(s => {
            const exp = formatExpiration(s.expires_at);
            const card = document.createElement('div');
            card.className = 'session-card';
            const burnBadge = s.burn_after_download ? '<span class="burn-badge">🔥 Ephemeral</span>' : '';
            card.innerHTML = `
                <div class="session-card-info">
                    <div class="session-card-title">
                        <h3>${formatSessionCode(s.session_code)}</h3>
                        <span class="${exp.className}">${s.status.toUpperCase()}</span>
                        ${burnBadge}
                    </div>
                    <div class="session-card-meta">
                        <span>${s.item_count || 0} file(s)</span>
                        <span>${formatBytes(s.total_size_bytes)}</span>
                        <span>${exp.text}</span>
                    </div>
                </div>
                <div class="session-card-actions">
                    <button type="button" class="btn btn-ghost btn-sm copy-btn" data-code="${s.session_code}">Copy Code</button>
                    <a class="btn btn-secondary btn-sm" href="/s/${s.session_code}">View</a>
                    <button type="button" class="btn btn-ghost btn-sm btn-delete delete-btn" data-id="${s.session_id}" title="Delete session">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle;">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            <line x1="10" y1="11" x2="10" y2="17"></line>
                            <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                    </button>
                </div>
            `;
            listEl.appendChild(card);
        });

        listEl.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const code = btn.dataset.code;
                try {
                    await navigator.clipboard.writeText(code);
                    const orig = btn.textContent;
                    btn.textContent = 'Copied!';
                    toast('Session code copied.');
                    setTimeout(() => { btn.textContent = orig; }, 1500);
                } catch {
                    toast('Could not copy code.', 'error');
                }
            });
        });

        listEl.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const sessionId = btn.dataset.id;
                if (!confirm('Are you sure you want to delete this transfer session and all its files?')) return;
                const token = getToken();
                try {
                    const resp = await fetch(`${API_PREFIX}/sessions/${sessionId}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!resp.ok) {
                        const err = await resp.json().catch(() => ({}));
                        throw new Error(err.detail || 'Could not delete session');
                    }
                    toast('Session deleted.');
                    loadSessions();
                } catch (err) {
                    toast(err.message, 'error');
                }
            });
        });
    }

    async function loadSessions() {
        const token = getToken();
        if (!token) {
            listEl.hidden = true;
            emptyEl.hidden = false;
            hintEl.textContent = 'Please sign in to view your transfers.';
            emptyEl.innerHTML = `
                <h2>Sign in required</h2>
                <p>Your transfer sessions are tied to your account.</p>
            `;
            return;
        }

        try {
            const resp = await fetch(`${API_PREFIX}/sessions/mine`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) {
                if (resp.status === 401) {
                    clearToken();
                    throw new Error('Session expired. Please sign in again.');
                }
                throw new Error('Could not fetch transfer history.');
            }
            sessions = await resp.json();
            renderSessions(sessions);
        } catch (err) {
            hintEl.textContent = err.message;
            toast(err.message, 'error');
        }
    }

    searchInput?.addEventListener('input', () => {
        const q = searchInput.value.trim().toLowerCase();
        if (!q) {
            renderSessions(sessions);
            return;
        }
        const filtered = sessions.filter(s => s.session_code.toLowerCase().includes(q));
        renderSessions(filtered);
    });

    loadSessions();
}

/* =========================================================
   INITIALIZATION
========================================================= */
document.addEventListener('DOMContentLoaded', () => {
    refreshAuthStatus();
    bindAuthForm();

    const page = document.body.dataset.page;
    const activeNavKey = (page === 'direct_session') ? 'download' : page;
    if (activeNavKey) {
        document.querySelectorAll(`[data-nav="${activeNavKey}"]`).forEach(el => el.classList.add('active'));
    }

    if (page === 'upload') setupUploadPage();
    else if (page === 'download') setupReceivePage();
    else if (page === 'direct_session') setupDirectSessionPage();
    else if (page === 'files') setupHistoryPage();
});
