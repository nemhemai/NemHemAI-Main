"""
Complete Setup Script for NemhemAI
Handles verification of bundled Python environment and installation of Ollama
"""
import os
import sys
import subprocess
import urllib.request
from pathlib import Path
import time

def get_app_data_dir():
    """Get the application data directory"""
    if sys.platform == 'win32':
        app_data = os.path.join(os.environ.get('APPDATA', ''), 'NemhemAI')
    elif sys.platform == 'darwin':
        app_data = os.path.expanduser('~/Library/Application Support/NemhemAI')
    else:
        app_data = os.path.expanduser('~/.nemhemai')
    
    os.makedirs(app_data, exist_ok=True)
    return app_data

def is_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, 
                              timeout=5)
        return result.returncode == 0
    except:
        return False

def is_ollama_running():
    """Check if Ollama server is running"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('localhost', 11434))
        s.close()
        return True
    except:
        return False

def download_file(url, destination, progress_callback=None):
    """Download a file with progress reporting"""
    def report_progress(block_num, block_size, total_size):
        if progress_callback and total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, (downloaded * 100) // total_size)
            progress_callback(f"Downloading Ollama... {percent}%")
    
    urllib.request.urlretrieve(url, destination, reporthook=report_progress)

def install_ollama(progress_callback=None):
    """Download and install Ollama"""
    if progress_callback:
        progress_callback("Preparing to install Ollama...")
    
    # Download Ollama installer
    ollama_url = "https://ollama.com/download/OllamaSetup.exe"
    temp_dir = os.path.join(os.environ.get('TEMP', ''), 'nemhemai_setup')
    os.makedirs(temp_dir, exist_ok=True)
    
    installer_path = os.path.join(temp_dir, 'OllamaSetup.exe')
    
    try:
        download_file(ollama_url, installer_path, progress_callback)
        
        if progress_callback:
            progress_callback("Installing Ollama (this may take a minute)...")
        
        # Run installer silently
        result = subprocess.run(
            [installer_path, '/S'],  # /S for silent install
            capture_output=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            if progress_callback:
                progress_callback("Ollama installed successfully!")
            
            # Wait a bit for Ollama to initialize
            time.sleep(3)
            return True
        else:
            raise Exception(f"Ollama installation failed with code {result.returncode}")
            
    except Exception as e:
        raise Exception(f"Failed to install Ollama: {str(e)}")
    finally:
        # Clean up installer
        if os.path.exists(installer_path):
            try:
                os.remove(installer_path)
            except:
                pass

def start_ollama_service(progress_callback=None):
    """Start Ollama service"""
    if is_ollama_running():
        if progress_callback:
            progress_callback("Ollama is already running ✓")
        return True
    
    if progress_callback:
        progress_callback("Starting Ollama service...")
    
    try:
        # Start Ollama in background
        subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        # Wait for service to start
        max_attempts = 30
        for i in range(max_attempts):
            if is_ollama_running():
                if progress_callback:
                    progress_callback("Ollama service started ✓")
                return True
            time.sleep(1)
            if progress_callback and i % 5 == 0:
                progress_callback(f"Starting Ollama service... ({i}s)")
        
        raise Exception("Ollama service failed to start")
        
    except Exception as e:
        raise Exception(f"Failed to start Ollama: {str(e)}")

def verify_python_environment(progress_callback=None):
    """Verify bundled Python environment has all required modules"""
    if progress_callback:
        progress_callback("Verifying bundled Python modules...")
    
    # Core modules that must be present
    required_modules = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('sklearn', 'Scikit-learn'),
    ]
    
    missing_modules = []
    for module_name, display_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(display_name)
    
    if missing_modules:
        error_msg = f"Bundled Python is missing modules: {', '.join(missing_modules)}\n"
        error_msg += "Please reinstall the application."
        raise Exception(error_msg)
    
    if progress_callback:
        progress_callback("All Python modules verified ✓")
    
    return True

def is_setup_complete():
    """Check if complete setup has been done"""
    app_data = get_app_data_dir()
    setup_flag = os.path.join(app_data, '.complete_setup_done')
    return os.path.exists(setup_flag)

def mark_setup_complete():
    """Mark complete setup as done"""
    app_data = get_app_data_dir()
    setup_flag = os.path.join(app_data, '.complete_setup_done')
    with open(setup_flag, 'w') as f:
        f.write('1')

def run_complete_setup(progress_callback=None):
    """Run complete first-time setup"""
    try:
        # Step 1: Verify Python environment
        verify_python_environment(progress_callback)
        
        # Step 2: Install Ollama if needed
        if not is_ollama_installed():
            if progress_callback:
                progress_callback("Ollama not found. Installing...")
            install_ollama(progress_callback)
        else:
            if progress_callback:
                progress_callback("Ollama is already installed")
        
        # Step 3: Start Ollama service
        start_ollama_service(progress_callback)
        
        # Step 4: Mark setup as complete
        mark_setup_complete()
        
        if progress_callback:
            progress_callback("Setup completed successfully!")
        
        return True
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"Setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("Running complete setup...")
    try:
        run_complete_setup(lambda msg: print(msg))
        print("Setup completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
