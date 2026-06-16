import os
import zipfile

def create_zip():
    zip_filename = "gov-verify-ai_shareable.zip"
    source_dir = "."
    
    # Directories and files to exclude
    exclude_dirs = {'venv', '.git', '__pycache__', 'storage', 'scratch', '.gemini'}
    exclude_files = {zip_filename, 'gov-verify-ai.zip'}

    print(f"Creating {zip_filename}...")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude unwanted directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.endswith('.egg-info')]
            
            for file in files:
                if file in exclude_files or file.endswith('.pyc'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                
    print(f"Successfully created {zip_filename}")
    print(f"Size: {os.path.getsize(zip_filename) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    create_zip()
