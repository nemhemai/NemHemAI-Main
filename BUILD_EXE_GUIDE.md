# Complete Guide to Build EXE for NemhemAI Project

## Prerequisites

### 1. Install Required Software
- **Python 3.10+** (already installed)
- **Node.js 18+** and npm (for frontend build)
- **PyInstaller** (for creating EXE)
- **Ollama** (must be installed and accessible)

### 2. Install Build Tools

```powershell
# Install PyInstaller
pip install pyinstaller

# Verify Node.js and npm are installed
node --version
npm --version
```

## Step-by-Step Build Process

### Step 1: Build the Frontend

```powershell
# Install frontend dependencies (if not already done)
npm install

# Build the React frontend for production
npm run build
```

This will create a `dist` folder with your compiled React application.

### Step 2: Install Python Dependencies

```powershell
# Navigate to backend directory
cd backend

# Install all required Python packages
pip install -r requirements.txt

# Go back to root directory
cd ..
```

### Step 3: Build the EXE

```powershell
# Run PyInstaller with the spec file
pyinstaller main.exe.spec
```

The EXE will be created in the `dist` folder.

### Step 4: Verify the Build

```powershell
# Run the executable
.\dist\main.exe
```

The application should:
1. Start the FastAPI backend server
2. Open your default browser to http://localhost:8000
3. Serve the React frontend

## Important Notes

### 1. **Ollama Dependency**
The application requires Ollama to be installed and running on the system:
- Download Ollama from: https://ollama.com/download
- Install it before running the EXE
- The required models will be pulled automatically on first run

### 2. **Database Files**
The EXE will create the following directories/files:
- `users.db` - User authentication database
- `databases/` - Data analysis databases
- `csv_uploads/` - Uploaded CSV files
- `uploads/` - Uploaded documents

### 3. **Environment Variables**
For production use, set these environment variables:
- `OPENROUTER_API_KEYS` - API keys for OpenRouter (optional)
- `EXA_API_KEY` - Exa search API key (optional)
- `TAVILY_API_KEY` - Tavily search API key (optional)
- `PORT` - Server port (default: 8000)
- `ALLOWED_ORIGINS` - CORS allowed origins

### 4. **File Size**
The EXE will be large (~200-500 MB) because it includes:
- Python interpreter
- All Python libraries
- Frontend React build files
- Required DLLs

## Troubleshooting

### Issue: "Module not found" errors
**Solution**: Add missing modules to `hiddenimports` in the spec file

### Issue: Frontend not loading
**Solution**: Ensure `dist` folder exists and is properly included in the spec file

### Issue: Database errors
**Solution**: Ensure write permissions in the directory where the EXE runs

### Issue: Ollama connection errors
**Solution**: 
- Install Ollama from https://ollama.com/download
- Ensure Ollama service is running (`ollama serve`)
- Check port 11434 is not blocked

## Distribution

When distributing your EXE:

1. **Include these files/folders:**
   - `main.exe` (the built executable)
   - `README.md` (usage instructions)
   
2. **User Requirements:**
   - Windows 10/11 (64-bit)
   - Ollama installed and running
   - Internet connection (for model downloads)
   - 2GB+ free disk space
   - 8GB+ RAM recommended

3. **First Run Instructions:**
   ```
   1. Install Ollama from https://ollama.com/download
   2. Double-click main.exe
   3. Wait for models to download (first run only)
   4. Browser will open automatically
   5. Register a new account
   ```

## Advanced Configuration

### Creating a Single-File EXE

The current spec file creates a single-file EXE. To create a directory-based distribution:

1. Edit `main.exe.spec`
2. Change `onefile=True` to `onefile=False`
3. Rebuild with PyInstaller

### Code Signing (Optional)

For professional distribution, sign your EXE:

```powershell
# Requires a code signing certificate
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com main.exe
```

## Automated Build Script

A `build.bat` script is provided for automated building. Run:

```powershell
.\build.bat
```

This will:
1. Clean previous builds
2. Build the frontend
3. Build the backend EXE
4. Create a release package

## Support

For issues or questions:
- Check the logs in the console window
- Verify Ollama is running
- Check firewall settings
- Ensure all prerequisites are installed
