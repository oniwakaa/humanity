const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill'); // Ensure we kill the process tree
const serve = require('electron-serve');

let mainWindow;
let backendProcess;
const IS_DEV = process.env.NODE_ENV === 'development';
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

async function waitForBackend(port, timeoutMs = 20000) {
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
            log(`Backend check failed: ${err.message}. Retrying...`);
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

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(async () => {
    await startBackend();

    // Wait for backend to be healthy before loading UI
    // Silent Polling Strategy: Verify connectivity continuously for grace period
    const isHealthy = await waitForBackend(BACKEND_PORT);

    if (!isHealthy) {
        log('WARNING: Backend failed health check, but proceeding with UI load.');
        dialog.showMessageBox({
            type: 'warning',
            title: 'Backend Warning',
            message: 'Backend server may not be ready',
            detail: 'The backend health check failed. The app may not function correctly. Check the console for details.'
        });
    }

    await createWindow();

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
