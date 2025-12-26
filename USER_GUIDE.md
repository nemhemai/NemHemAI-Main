# NemhemAI - User Guide

## What is NemhemAI?

NemhemAI is an AI-powered chat assistant with advanced features including:
- Multiple AI model support (via Ollama)
- Document analysis (PDF, DOCX, images)
- Data analysis with CSV files
- Web search integration
- Chat history and sessions

## System Requirements

- **Operating System**: Windows 10/11 (64-bit)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk Space**: 10 GB free space (for models)
- **Internet**: Required for model downloads and web search

## Installation Instructions

### Step 1: Install Ollama

Before running NemhemAI, you **must** install Ollama:

1. Download Ollama from: **https://ollama.com/download**
2. Run the Ollama installer
3. Wait for installation to complete
4. Ollama will start automatically in the background

### Step 2: Run NemhemAI

1. Double-click **NemhemAI.exe**
2. A console window will appear showing the startup process
3. Your default web browser will open automatically
4. Wait for the application to load (first run may take 2-3 minutes)

### First Run

On the first run, NemhemAI will:
1. Download required AI models (this may take 5-10 minutes)
2. Set up the database
3. Open the web interface

**Please be patient during the first startup!**

## Using NemhemAI

### 1. Create an Account

- Click "Register" on the login page
- Choose a username and password
- Your account is stored locally on your computer

### 2. Start Chatting

- Type your questions in the chat box
- Select an AI model from the dropdown
- Press Enter or click Send
- The AI will respond with streaming text

### 3. Upload Documents

- Click the upload button
- Select PDF, DOCX, or image files
- The content will be extracted and used as context
- Ask questions about your documents

### 4. Data Analysis

- Upload CSV files
- Ask questions about your data
- NemhemAI will generate Python code
- View charts and statistics automatically

### 5. Web Search

- Enable web search in settings
- Your queries will include recent information from the internet
- Multiple search engines are used for comprehensive results

## Available AI Models

The following models are included:
- **Llama 3.1** - General purpose, good for most tasks
- **Mistral** - Fast and efficient
- **DeepSeek Coder** - Best for programming and data analysis
- **And more...**

## Troubleshooting

### Issue: "Connection Error" or "Ollama not found"

**Solution**: 
1. Ensure Ollama is installed
2. Open Task Manager and check if "ollama" process is running
3. Restart Ollama: Open Command Prompt and type `ollama serve`

### Issue: Application won't start

**Solution**:
1. Check if port 8000 is available
2. Close other applications using port 8000
3. Run as Administrator

### Issue: Models not downloading

**Solution**:
1. Check your internet connection
2. Ensure you have enough disk space (10GB+)
3. Wait patiently - large models take time to download

### Issue: Slow performance

**Solution**:
1. Close other applications
2. Use smaller models (like Llama 3.2 1B)
3. Ensure you have at least 8GB RAM available

### Issue: Browser doesn't open automatically

**Solution**:
1. Manually open your browser
2. Go to: **http://localhost:8000**

## Data Storage

NemhemAI stores data in these locations:
- **users.db** - Your account information
- **csv_uploads/** - Your uploaded CSV files
- **uploads/** - Your uploaded documents
- **databases/** - Analysis databases

All data is stored locally on your computer.

## Privacy & Security

- All data is stored locally
- No information is sent to external servers (except AI API calls)
- Your documents are processed on your machine
- Account passwords are securely hashed

## Uninstallation

To remove NemhemAI:
1. Delete **NemhemAI.exe**
2. Delete the database files (users.db, etc.)
3. Uninstall Ollama from Windows Settings (if desired)

## Support

For issues or questions:
- Check the console window for error messages
- Ensure all prerequisites are installed
- Verify Ollama is running

## Advanced Settings

### Change Port

To run on a different port:
1. Open Command Prompt in the same folder as NemhemAI.exe
2. Set PORT environment variable:
   ```
   set PORT=8080
   NemhemAI.exe
   ```

### Use Custom Models

To use additional Ollama models:
1. Open Command Prompt
2. Pull the model: `ollama pull model-name`
3. The model will appear in NemhemAI's model selector

## Credits

Powered by:
- FastAPI (Backend)
- React (Frontend)
- Ollama (AI Models)
- SQLite (Database)

---

**Enjoy using NemhemAI!** 🚀
