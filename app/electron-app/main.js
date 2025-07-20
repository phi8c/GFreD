const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');
const axios = require('axios'); // Phải cài thêm: npm install axios

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    fullscreen: true,
    frame: false,
    kiosk: true, // Không thể thoát bằng tổ hợp phím thông thường (nâng cao hơn fullscreen)
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.setMenuBarVisibility(false);

  mainWindow.loadURL('http://localhost:5000/join-room');

  // Chặn DevTools
  mainWindow.webContents.on('before-input-event', (event, input) => {
    const key = input.key.toLowerCase();

    const blockedCombos = [
      key === 'f12',
      key === 'i' && input.control && input.shift, // Ctrl+Shift+I
      key === 'w' && input.control,                // Ctrl+W
      key === 'r' && input.control,                // Ctrl+R (reload)
      key === 'f4' && input.alt                    // Alt+F4
    ];

    if (blockedCombos.some(Boolean)) {
      event.preventDefault();
      sendLog('Blocked key combination detected: ' + input.key);
    }
  });

  // Theo dõi khi học sinh rời cửa sổ
  mainWindow.on('blur', () => {
    sendLog('User switched window or lost focus.');
  });
}

// Gửi log về Flask backend
function sendLog(message) {
  axios.post('http://localhost:5000/log-event', { message })
    .catch(err => console.error('Failed to send log:', err.message));
}

app.whenReady().then(() => {
  // Chặn Command/Ctrl + Q
  globalShortcut.register('CommandOrControl+Q', () => {
    sendLog('Attempted to quit app');
  });

  createWindow();
});

// Đóng hoàn toàn app
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
