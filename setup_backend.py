"""
Backend Setup Script
This script handles first-time setup of Python dependencies
"""
import os
import sys
import subprocess
import json
from pathlib import Path

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

def is_setup_complete():
    """Check if setup has been completed"""
    app_data = get_app_data_dir()
    setup_flag = os.path.join(app_data, '.setup_complete')
    return os.path.exists(setup_flag)

def mark_setup_complete():
    """Mark setup as complete"""
    app_data = get_app_data_dir()
    setup_flag = os.path.join(app_data, '.setup_complete')
    with open(setup_flag, 'w') as f:
        f.write('1')

def get_python_executable():
    """Get the Python executable path"""
    # Check if we're in a bundled environment
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Try to find bundled Python
    if sys.platform == 'win32':
        python_paths = [
            os.path.join(base_path, 'python', 'python.exe'),
            os.path.join(base_path, '..', 'python', 'python.exe'),
            'python',
            'python3'
        ]
    else:
        python_paths = [
            os.path.join(base_path, 'python', 'bin', 'python3'),
            os.path.join(base_path, '..', 'python', 'bin', 'python3'),
            'python3',
            'python'
        ]
    
    for python_path in python_paths:
        try:
            result = subprocess.run([python_path, '--version'], 
                                  capture_output=True, 
                                  timeout=5)
            if result.returncode == 0:
                return python_path
        except:
            continue
    
    return None

def install_requirements(progress_callback=None):
    """Install Python requirements"""
    python_exe = get_python_executable()
    
    if not python_exe:
        raise Exception("Python not found. Please install Python 3.11 or later.")
    
    # Get requirements file path
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    requirements_file = os.path.join(base_path, 'backend', 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        raise Exception(f"Requirements file not found: {requirements_file}")
    
    if progress_callback:
        progress_callback("Installing Python dependencies...")
    
    # Upgrade pip first
    subprocess.run([python_exe, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                  capture_output=True)
    
    # Install requirements
    result = subprocess.run(
        [python_exe, '-m', 'pip', 'install', '-r', requirements_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to install requirements:\n{result.stderr}")
    
    if progress_callback:
        progress_callback("Installation complete!")
    
    mark_setup_complete()
    return True

def run_setup_if_needed(progress_callback=None):
    """Run setup if it hasn't been completed"""
    if not is_setup_complete():
        if progress_callback:
            progress_callback("First-time setup in progress...")
        return install_requirements(progress_callback)
    return True

if __name__ == "__main__":
    print("Running backend setup...")
    try:
        run_setup_if_needed(lambda msg: print(msg))
        print("Setup completed successfully!")
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
