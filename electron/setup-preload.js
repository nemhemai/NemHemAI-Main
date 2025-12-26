const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onSetupProgress: (callback) => {
    ipcRenderer.on('setup-progress', (event, message) => callback(message));
  }
});
