const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
    // expose specific ipc methods if needed
    // platform: process.platform
});
