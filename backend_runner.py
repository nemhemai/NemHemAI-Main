import os
import sys
import uvicorn
import multiprocessing

# Add the current directory to sys.path so backend module can be found
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting backend server on port {port}")
    # Use 127.0.0.1 to avoid firewall prompts sometimes
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
