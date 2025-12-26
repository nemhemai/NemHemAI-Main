const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const axios = require('axios');
const isDev = require('electron-is-dev');
const fs = require('fs');

let mainWindow;
let backendProcess;
const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// Python backend management
function startBackend() {
  return new Promise(async (resolve, reject) => {
    console.log('🚀 Starting Python backend...');
    
    // Determine Python executable path
    let pythonPath;
    let backendScript;
    let setupScript;
    
    if (isDev) {
      // Development mode - use local Python
      pythonPath = process.platform === 'win32' ? 'python' : 'python3';
      backendScript = path.join(__dirname, '..', 'backend', 'main.py');
      setupScript = path.join(__dirname, '..', 'setup_complete.py');
    } else {
      // Production mode - use bundled Python
      const bundledPythonDir = path.join(process.resourcesPath, 'python');
      
      if (process.platform === 'win32') {
        pythonPath = path.join(bundledPythonDir, 'python.exe');
      } else if (process.platform === 'darwin') {
        pythonPath = path.join(bundledPythonDir, 'bin', 'python3');
      } else {
        pythonPath = path.join(bundledPythonDir, 'bin', 'python3');
      }
      
      // Verify bundled Python exists
      if (!fs.existsSync(pythonPath)) {
        console.error('❌ Bundled Python not found at:', pythonPath);
        reject(new Error('Bundled Python not found. Please reinstall the application.'));
        return;
      }
      
      backendScript = path.join(process.resourcesPath, 'backend', 'main.py');
      setupScript = path.join(process.resourcesPath, 'setup_complete.py');
      
      console.log('✅ Using bundled Python:', pythonPath);
    }

    console.log(`Python path: ${pythonPath}`);
    console.log(`Backend script: ${backendScript}`);

    // Check if first-time setup is needed
    const appData = process.platform === 'win32' 
      ? path.join(process.env.APPDATA || '', 'NemhemAI')
      : process.platform === 'darwin'
        ? path.join(require('os').homedir(), 'Library', 'Application Support', 'NemhemAI')
        : path.join(require('os').homedir(), '.nemhemai');
    
    const setupFlag = path.join(appData, '.complete_setup_done');
    
    // Run first-time setup if needed (for Ollama installation)
    if (!fs.existsSync(setupFlag) && fs.existsSync(setupScript)) {
      console.log('🔧 Running first-time setup (Ollama installation)...');
      
      try {
        // Show setup window
        const setupWindow = createSetupWindow();
        
        // Run setup script
        const setupProcess = spawn(pythonPath, [setupScript], {
          cwd: isDev ? path.join(__dirname, '..') : process.resourcesPath,
        });

        let setupOutput = '';
        
        setupProcess.stdout.on('data', (data) => {
          const message = data.toString().trim();
          console.log(`[Setup] ${message}`);
          setupOutput += message + '\n';
          
          // Update setup window
          if (setupWindow && !setupWindow.isDestroyed()) {
            setupWindow.webContents.send('setup-progress', message);
          }
        });

        setupProcess.stderr.on('data', (data) => {
          const message = data.toString().trim();
          console.error(`[Setup Error] ${message}`);
          
          // Update setup window with errors too
          if (setupWindow && !setupWindow.isDestroyed()) {
            setupWindow.webContents.send('setup-progress', message);
          }
        });

        await new Promise((resolveSetup, rejectSetup) => {
          setupProcess.on('close', (code) => {
            if (setupWindow && !setupWindow.isDestroyed()) {
              setupWindow.close();
            }
            
            if (code === 0) {
              console.log('✅ Setup completed successfully');
              resolveSetup();
            } else {
              console.error('❌ Setup failed with code:', code);
              rejectSetup(new Error(`Setup failed with code ${code}\n${setupOutput}`));
            }
          });
        });
      } catch (error) {
        console.error('Setup error:', error);
        reject(error);
        return;
      }
    } else {
      console.log('✅ Setup already completed, skipping...');
    }

    // Set environment variable for desktop mode
    const env = { ...process.env, DESKTOP_MODE: '1', PORT: BACKEND_PORT.toString() };

    // Start the backend process
    backendProcess = spawn(pythonPath, [backendScript], {
      env,
      cwd: isDev ? path.join(__dirname, '..') : process.resourcesPath,
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`[Backend] ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`[Backend Error] ${data.toString().trim()}`);
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
    });

    // Wait for backend to be ready
    waitForBackend(resolve, reject);
  });
}

function waitForBackend(resolve, reject, attempts = 0) {
  // No timeout - wait indefinitely for backend to start
  
  axios.get(`${BACKEND_URL}/health`, { timeout: 1000 })
    .then(() => {
      console.log('✅ Backend is ready!');
      resolve();
    })
    .catch(() => {
      if (attempts % 10 === 0) {
        console.log(`⏳ Waiting for backend... (${attempts / 2} seconds)`);
      }
      setTimeout(() => waitForBackend(resolve, reject, attempts + 1), 500);
    });
}

function createSetupWindow() {
  const setupWindow = new BrowserWindow({
    width: 500,
    height: 300,
    resizable: false,
    frame: false,
    backgroundColor: '#1a1a1a',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'setup-preload.js')
    }
  });

  // Create a simple HTML page for setup progress
  const setupHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          margin: 0;
          padding: 0;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 100vh;
        }
        .container {
          text-align: center;
          padding: 40px;
        }
        h1 {
          font-size: 24px;
          margin-bottom: 20px;
        }
        .spinner {
          border: 4px solid rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          border-top: 4px solid white;
          width: 50px;
          height: 50px;
          animation: spin 1s linear infinite;
          margin: 20px auto;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .message {
          margin-top: 20px;
          font-size: 14px;
          opacity: 0.9;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>🚀 Setting up NemhemAI</h1>
        <div class="spinner"></div>
        <div class="message" id="progress">Installing dependencies...</div>
      </div>
      <script>
        window.electronAPI?.onSetupProgress((message) => {
          document.getElementById('progress').textContent = message;
        });
      </script>
    </body>
    </html>
  `;

  setupWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(setupHtml));
  setupWindow.show();

  return setupWindow;
}

function stopBackend() {
  if (backendProcess) {
    console.log('🛑 Stopping backend...');
    backendProcess.kill();
    backendProcess = null;
  }
}

// Create the main application window
function createWindow() {
  // Determine icon path
  let iconPath;
  if (process.platform === 'win32') {
    iconPath = path.join(__dirname, 'build', 'icon.ico');
  } else if (process.platform === 'darwin') {
    iconPath = path.join(__dirname, 'build', 'icon.icns');
  } else {
    iconPath = path.join(__dirname, 'build', 'icon.png');
  }

  // Check if icon exists, otherwise use undefined (Electron default)
  if (!fs.existsSync(iconPath)) {
    console.log('⚠️  Custom icon not found, using default Electron icon');
    iconPath = undefined;
  }

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    backgroundColor: '#FFFFFF',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true,
    },
    icon: iconPath,
    show: false, // Don't show until ready
  });

  // Create application menu
  const menuTemplate = [
    {
      label: 'File',
      submenu: [
        {
          label: 'New Chat',
          accelerator: 'CmdOrCtrl+N',
          click: () => {
            mainWindow.webContents.reload();
          }
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            app.quit();
          }
        }
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
      label: 'Help',
      submenu: [
        {
          label: 'About NemhemAI',
          click: () => {
            const { dialog } = require('electron');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About NemhemAI',
              message: 'NemhemAI - AI Chat Assistant',
              detail: 'Version 1.0.0\n\nA powerful AI chat interface with multiple model support.',
              buttons: ['OK']
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  // Load the app
  const startUrl = isDev
    ? 'http://localhost:8001' // Vite dev server
    : `file://${path.join(__dirname, '..', 'dist', 'index.html')}`; // Production: load bundled frontend

  console.log(`📂 Loading URL: ${startUrl}`);

  // Add timeout to show window even if loading fails
  const showTimeout = setTimeout(() => {
    if (mainWindow && !mainWindow.isVisible()) {
      console.log('⚠️  Window not shown after 10 seconds, forcing show...');
      mainWindow.show();
    }
  }, 10000); // 10 second timeout

  mainWindow.loadURL(startUrl);

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    clearTimeout(showTimeout);
    mainWindow.show();
    console.log('🪟 Application window opened');
  });

  // Handle load failures
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error(`❌ Failed to load: ${errorCode} - ${errorDescription}`);
    clearTimeout(showTimeout);
    mainWindow.show();
  });

  // Log console messages from renderer
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer] ${message}`);
  });

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });
}

// App lifecycle
app.whenReady().then(async () => {
  console.log('='.repeat(50));
  console.log('     NemhemAI - Desktop Application');
  console.log('='.repeat(50));
  console.log(`Environment: ${isDev ? 'Development' : 'Production'}`);
  console.log(`Platform: ${process.platform}`);
  console.log(`Electron: ${process.versions.electron}`);
  console.log(`Node: ${process.versions.node}`);
  console.log('='.repeat(50));
  
  let backendStarted = false;
  
  try {
    // Start backend first
    console.log('🔄 Starting backend...');
    await startBackend();
    backendStarted = true;
    console.log('✅ Backend started successfully');
  } catch (error) {
    console.error('❌ Failed to start backend:', error);
    console.error('Stack:', error.stack);
    
    // Show error dialog
    const { dialog } = require('electron');
    dialog.showErrorBox(
      'Backend Startup Failed',
      `Failed to start the Python backend:\n\n${error.message}\n\nThe application will start, but some features may not work.`
    );
  }
  
  // Always create window, even if backend failed
  try {
    console.log('🔄 Creating application window...');
    createWindow();
    console.log('✅ Window created');
  } catch (error) {
    console.error('❌ Failed to create window:', error);
    console.error('Stack:', error.stack);
    
    // Show error and quit
    const { dialog } = require('electron');
    dialog.showErrorBox(
      'Application Startup Failed',
      `Failed to create application window:\n\n${error.message}\n\nThe application will now exit.`
    );
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// Handle any uncaught errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});
