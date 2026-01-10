const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const http = require('http');
const treeKill = require('tree-kill');
const serve = require('electron-serve');

let mainWindow;
let backendProcess;
const IS_DEV = !app.isPackaged;
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 3000;

// Initialize electron-serve for production builds
const loadURL = IS_DEV ? null : serve({ directory: path.join(__dirname, '../out') });

// Path to backend executable or script
const binaryName = process.platform === 'win32' ? 'humanity-backend.exe' : 'humanity-backend';
const BACKEND_PATH = IS_DEV
    ? path.join(__dirname, '../../venv/bin/python')
    : path.join(process.resourcesPath, 'backend', binaryName);

const BACKEND_ARGS = IS_DEV
    ? [path.join(__dirname, '../../api/server.py')]
    : [];

function log(msg) {
    console.log(`[Main] ${msg}`);
}

// Kill any existing backend processes
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
                log('No zombie processes found.');
            }
            resolve();
        });
    });
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
    log(`Waiting for backend on port ${port}...`);

    while (Date.now() - start < timeoutMs) {
        try {
            const isReady = await new Promise((resolve, reject) => {
                const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
                    if (res.statusCode === 200) {
                        res.resume();
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
            await sleep(1000);
        }
    }
    log('Backend timed out.');
    return false;
}

async function startBackend() {
    await killOldProcesses();
    log(`Starting backend from: ${BACKEND_PATH}`);

    const fs = require('fs');
    if (!IS_DEV && !fs.existsSync(BACKEND_PATH)) {
        console.error(`[Error] Backend binary NOT FOUND at: ${BACKEND_PATH}`);
        dialog.showErrorBox('Backend Error', `Binary not found at:\n${BACKEND_PATH}`);
        return;
    }

    try {
        const userDataPath = app.getPath('userData');
        backendProcess = spawn(BACKEND_PATH, BACKEND_ARGS, {
            cwd: IS_DEV ? path.join(__dirname, '../..') : path.join(process.resourcesPath, 'backend'),
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                HUMANITY_DATA_DIR: userDataPath
            }
        });

        backendProcess.stdout.on('data', (data) => {
            log(`[Backend] ${data}`);
        });

        backendProcess.stderr.on('data', (data) => {
            console.error(`[Backend Warn] ${data}`);
        });

        backendProcess.on('close', (code) => {
            log(`Backend exited with code ${code}`);
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

async function createWindow() {
    // Don't create if window already exists
    if (mainWindow && !mainWindow.isDestroyed()) {
        log('Window already exists, showing instead.');
        mainWindow.show();
        return mainWindow;
    }

    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        show: true, // Show immediately
        backgroundColor: '#ffffff',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webSecurity: false
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
        // On macOS, we keep the reference but mark as destroyed
        // The app lifecycle handler will recreate if needed
        mainWindow = null;
    });

    return mainWindow;
}

// ===============================
// App Lifecycle
// ===============================

app.whenReady().then(async () => {
    log('App ready');

    // Create menu (required for some macOS features)
    createMenu();

    // 1. Start Backend Immediately
    startBackend();

    // 2. Wait for Backend Health
    const isHealthy = await waitForBackend(BACKEND_PORT, 120000);

    if (!isHealthy) {
        log('WARNING: Backend failed health check.');
        dialog.showErrorBox('Backend Error', 'The backend failed to start. Please check logs.');
        app.quit();
        return;
    }

    // 3. Create Main Window
    await createWindow();
});

// macOS: Re-create or show window when clicking Dock icon
app.on('activate', async () => {
    log('App activated');
    if (!mainWindow || mainWindow.isDestroyed()) {
        // Window was closed or never created - create new one
        await createWindow();
    } else {
        // Window exists but may be hidden - show it
        mainWindow.show();
        mainWindow.focus();
    }
});

// macOS: Prevent quitting when all windows closed (app stays running in dock)
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Clean shutdown
app.on('will-quit', () => {
    stopBackend();
});

// Application menu (basic template)
function createMenu() {
    const { Menu } = require('electron');
    
    const template = [
        {
            label: 'Humanity',
            submenu: [
                { role: 'about' },
                { type: 'separator' },
                { role: 'services' },
                { type: 'separator' },
                { role: 'hide' },
                { role: 'hideOthers' },
                { role: 'unhide' },
                { type: 'separator' },
                { role: 'quit' }
            ]
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Window',
            submenu: [
                { role: 'minimize' },
                { role: 'zoom' },
                { type: 'separator' },
                { role: 'front' }
            ]
        }
    ];

    if (process.platform === 'darwin') {
        // Add app name to first menu
        template[0].label = app.getName();
    }

    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}
