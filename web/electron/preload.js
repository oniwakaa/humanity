const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
    ipcRenderer: {
        send: (channel, data) => ipcRenderer.send(channel, data),
        on: (channel, func) => {
            const subscription = (_event, ...args) => func(_event, ...args);
            ipcRenderer.on(channel, subscription);
            return () => ipcRenderer.removeListener(channel, subscription);
        },
        once: (channel, func) => ipcRenderer.once(channel, (_event, ...args) => func(_event, ...args))
    }
});
