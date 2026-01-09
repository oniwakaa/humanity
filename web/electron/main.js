const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill'); // Ensure we kill the process tree
const serve = require('electron-serve');

let mainWindow;
let backendProcess;
const IS_DEV = !app.isPackaged;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

// Initialize electron-serve for production builds
const loadURL = IS_DEV ? null : serve({ directory: path.join(__dirname, '../out') });

// Path to backend executable or script
const BACKEND_PATH = IS_DEV
    ? path.join(__dirname, '../../venv/bin/python') // Dev: Use venv python
    : path.join(process.resourcesPath, 'backend', 'humanity-backend'); // Prod: Bundled binary

const BACKEND_ARGS = IS_DEV
    ? [path.join(__dirname, '../../api/server.py')]
    : [];

function log(msg) {
    console.log(`[Main] ${msg}`);
}

// Helper to kill any existing backend processes (Scorched Earth Policy)
function killOldProcesses() {
    return new Promise((resolve) => {
        log('Checking for zombie backend processes...');
        const cmd = process.platform === 'win32'
            ? 'taskkill /F /IM humanity-backend.exe'
            : 'pkill -f humanity-backend';

        exec(cmd, (err, stdout, stderr) => {
            if (!err) {
                log('Killed old backend processes.');
            } else {
                // Error code 1 usually means no process found, which is good
                log('No zombie processes found (or failed to kill).');
            }
            resolve();
        });
    });
}

async function startBackend() {
    // Ensure clean slate
    await killOldProcesses();

    log(`Starting backend from: ${BACKEND_PATH}`);

    // Verify file exists (helper for debugging)
    const fs = require('fs');
    if (!IS_DEV && !fs.existsSync(BACKEND_PATH)) {
        console.error(`[Error] Backend binary NOT FOUND at: ${BACKEND_PATH}`);
        dialog.showErrorBox('Backend Error', `Binary not found at:\n${BACKEND_PATH}`);
        return;
    }

    try {
        backendProcess = spawn(BACKEND_PATH, BACKEND_ARGS, {
            cwd: IS_DEV ? path.join(__dirname, '../..') : path.join(process.resourcesPath, 'backend'),
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });

        backendProcess.stdout.on('data', (data) => {
            log(`[Backend] ${data}`);
        });

        backendProcess.stderr.on('data', (data) => {
            console.error(`[Backend Warn] ${data}`);
        });

        backendProcess.on('close', (code) => {
            log(`Backend exited with code ${code}`);
            if (code !== 0 && code !== null) {
                dialog.showErrorBox('Backend Exited', `Backend process exited with code ${code}.\nCheck logs for details.`);
            }
            backendProcess = null;
        });

        backendProcess.on('error', (err) => {
            console.error('[Error] Failed to start backend:', err);
            dialog.showErrorBox('Backend Start Failed', `Failed to spawn backend:\n${err.message}`);
        });
    } catch (e) {
        console.error('[Error] Exception spawning backend:', e);
        dialog.showErrorBox('Backend Exception', `Exception spawning backend:\n${e.message}`);
    }
}

function stopBackend() {
    if (backendProcess) {
        log('Stopping backend process tree...');
        treeKill(backendProcess.pid, 'SIGKILL', (err) => {
            if (err) {
                console.error('Failed to kill backend:', err);
            } else {
                log('Backend killed successfully.');
                backendProcess = null;
            }
        });
    }
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function waitForBackend(port, timeoutMs = 60000) {
    const start = Date.now();
    log(`Waiting for backend on port ${port}... (Timeout: ${timeoutMs}ms)`);

    while (Date.now() - start < timeoutMs) {
        try {
            const isReady = await new Promise((resolve, reject) => {
                const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
                    if (res.statusCode === 200) {
                        res.resume(); // consume any data
                        resolve(true);
                    } else {
                        res.resume();
                        reject(new Error(`Status: ${res.statusCode}`));
                    }
                });

                req.on('error', (err) => reject(err));
                req.setTimeout(1000, () => {
                    req.destroy();
                    reject(new Error('Request timeout'));
                });
            });

            if (isReady) {
                log('Backend is healthy!');
                return true;
            }
        } catch (err) {
            // log(`Backend check failed: ${err.message}. Retrying...`);
            await sleep(1000);
        }
    }

    log('Backend timed out.');
    return false;
}

async function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        show: false, // Don't show immediately
        backgroundColor: '#ffffff', // Prevent white flash (or match theme)
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webSecurity: false // Allow app:// to talk to http:// (Mixed Content / CORS bypass)
        }
    });

    if (IS_DEV) {
        const startUrl = `http://localhost:${FRONTEND_PORT}`;
        log(`Loading interface from: ${startUrl}`);
        mainWindow.loadURL(startUrl);
    } else {
        log('Loading interface from: app://-');
        await loadURL(mainWindow);
    }

    if (IS_DEV) {
        mainWindow.webContents.openDevTools();
    }

    // Wait for content to be ready before showing
    mainWindow.once('ready-to-show', () => {
        log('Main Window ready to show.');
        mainWindow.show();

        // Close splash after main window is visible
        if (splashWindow) {
            splashWindow.close();
            splashWindow = null;
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

let splashWindow;

// Optimized Backend Startup
// 1. Start Backend Immediately (don't wait for UI)
// 2. Parse stdout for progress updates
// 3. Show Splash
// 4. Show Main when ready

// Helper to wait for a URL to be serving (Retry loop)
async function waitForUrl(url, timeoutMs = 15000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        try {
            await new Promise((resolve, reject) => {
                const req = http.get(url, (res) => {
                    if (res.statusCode === 200) resolve();
                    else reject();
                });
                req.on('error', reject);
                req.end();
            });
            return true;
        } catch (e) {
            await sleep(500);
        }
    }
    return false;
}

async function createSplashWindow() {
    splashWindow = new BrowserWindow({
        width: 400,
        height: 300,
        frame: false,
        alwaysOnTop: true,
        transparent: true,
        center: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        }
    });

    const splashUrl = IS_DEV
        ? `http://localhost:${FRONTEND_PORT}/splash`
        : `app://-/splash.html`;

    // In Dev, wait for Next.js to be ready
    if (IS_DEV) {
        // log('Waiting for Frontend dev server...'); // Optional verbose log
        await waitForUrl(`http://localhost:${FRONTEND_PORT}`, 15000);
    }

    try {
        if (splashWindow && !splashWindow.isDestroyed()) {
            splashWindow.loadURL(splashUrl);
        }
    } catch (e) {
        log(`Failed to load splash URL: ${e.message}`);
    }

    splashWindow.on('closed', () => {
        splashWindow = null;
    });
}

function updateSplashStatus(status, progress) {
    if (splashWindow && !splashWindow.isDestroyed()) {
        splashWindow.webContents.send('init-status', { status, progress });
    }
}

async function startBackendAndTrackProgress() {
    // Ensure clean slate
    await killOldProcesses();

    log(`Starting backend from: ${BACKEND_PATH}`);

    // Verify file exists (helper for debugging)
    const fs = require('fs');
    if (!IS_DEV && !fs.existsSync(BACKEND_PATH)) {
        console.error(`[Error] Backend binary NOT FOUND at: ${BACKEND_PATH}`);
        dialog.showErrorBox('Backend Error', `Binary not found at:\n${BACKEND_PATH}`);
        return;
    }

    try {
        backendProcess = spawn(BACKEND_PATH, BACKEND_ARGS, {
            cwd: IS_DEV ? path.join(__dirname, '../..') : path.join(process.resourcesPath, 'backend'),
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                PYTHONPATH: IS_DEV ? path.join(__dirname, '../..') : undefined
            } // Force unbuffered stdout for real-time logs
        });

        backendProcess.stdout.on('data', (data) => {
            const msg = data.toString().trim();
            log(`[Backend] ${msg}`);

            // Parse [STATUS] content
            // Expected format: [STATUS] progress_pct || Message
            // Example: [STATUS] 10 || Loading Models...
            if (msg.includes('[STATUS]')) {
                const parts = msg.split('[STATUS]')[1].split('||');
                if (parts.length >= 2) {
                    const pct = parseFloat(parts[0].trim());
                    const text = parts[1].trim();
                    updateSplashStatus(text, pct);
                }
            }
        });

        backendProcess.stderr.on('data', (data) => {
            console.error(`[Backend Warn] ${data}`);
        });

        backendProcess.on('close', (code) => {
            log(`Backend exited with code ${code}`);
            if (code !== 0 && code !== null) {
                // connection lost
            }
            backendProcess = null;
        });

        backendProcess.on('error', (err) => {
            console.error('[Error] Failed to start backend:', err);
            dialog.showErrorBox('Backend Start Failed', `Failed to spawn backend:\n${err.message}`);
        });

    } catch (e) {
        console.error('[Error] Exception spawning backend:', e);
        dialog.showErrorBox('Backend Exception', `Exception spawning backend:\n${e.message}`);
    }
}


app.whenReady().then(async () => {
    // 1. Show Splash Immediately
    createSplashWindow();

    // 2. Start Backend & Track Progress
    startBackendAndTrackProgress();

    // 3. Wait for Backend Health (while splash shows progress)
    // We give it a generous timeout because the splash screen keeps user engaged
    const isHealthy = await waitForBackend(BACKEND_PORT, 120000);

    if (!isHealthy) {
        log('WARNING: Backend failed health check.');
        if (splashWindow) splashWindow.close();
        dialog.showErrorBox('Backend Error', 'The backend failed to start. Please check logs.');
        app.quit();
        return;
    }

    // 4. Create Main Window (Hidden initially if needed, but we just show it)
    await createWindow();

    // 5. Close Splash - Handled in createWindow 'ready-to-show'
    // if (splashWindow) {
    //     splashWindow.close();
    // }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    stopBackend();
});
