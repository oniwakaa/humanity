import os
import sys
import subprocess
import shutil
from pathlib import Path

# Config
VENDOR_DIR = Path("vendor")
WHISPER_DIR = VENDOR_DIR / "whisper.cpp"
MODELS_DIR = Path("models")
MODEL_NAME = "ggml-base.en.bin"
MODEL_PATH = MODELS_DIR / MODEL_NAME
REPO_URL = "https://github.com/ggerganov/whisper.cpp.git"

def run_cmd(cmd, cwd=None, check=True):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=False)
    if check and result.returncode != 0:
        print(f"Error running command: {cmd}")
        sys.exit(result.returncode)
    return result

def check_dependencies():
    print("--- 1. Checking Dependencies ---")
    deps = ["git", "make", "gcc"] # On Mac, gcc is usually clang alias
    missing = []
    for dep in deps:
        if not shutil.which(dep):
            missing.append(dep)
    
    if missing:
        print(f"ERROR: Missing system dependencies: {', '.join(missing)}")
        print("Please install them (e.g., 'xcode-select --install' on macOS).")
        sys.exit(1)
    print("✔ Dependencies OK.")

def setup_whisper():
    print("--- 2. Setting up whisper.cpp ---")
    VENDOR_DIR.mkdir(exist_ok=True)
    
    if not WHISPER_DIR.exists():
        print(f"Cloning whisper.cpp to {WHISPER_DIR}...")
        run_cmd(["git", "clone", REPO_URL, str(WHISPER_DIR)])
    else:
        print(f"whisper.cpp already exists at {WHISPER_DIR}.")

    print("Building whisper.cpp...")
    # Clean first just in case
    # run_cmd(["make", "clean"], cwd=WHISPER_DIR, check=False)
    run_cmd(["make"], cwd=WHISPER_DIR)
    
    # Check for executable in likely locations
    possible_paths = [
        WHISPER_DIR / "build" / "bin" / "whisper-cli",
        WHISPER_DIR / "build" / "bin" / "main",
        WHISPER_DIR / "main",
        WHISPER_DIR / "whisper-cli"
    ]
    
    found_exe = None
    for p in possible_paths:
        if p.exists():
            found_exe = p
            break
            
    if not found_exe:
        print("ERROR: Build failed. Executable (whisper-cli or main) not found.")
        sys.exit(1)
    
    print(f"✔ Build OK. Found executable at {found_exe}")
    return found_exe

def setup_model():
    print("--- 3. Checking Model ---")
    MODELS_DIR.mkdir(exist_ok=True)
    
    if not MODEL_PATH.exists():
        print(f"Model file not found at {MODEL_PATH}")
        print("You can download it using the whisper.cpp download script.")
        
        # Check if user wants to download
        # Automated script should conceptually be non-interactive or use args, 
        # but for this MVP setup we can try to use the downloader tool.
        
        download_script = WHISPER_DIR / "models" / "download-ggml-model.sh"
        if not download_script.exists():
             print(f"ERROR: Download script not found at {download_script}")
             sys.exit(1)

        print(f"Attempting to download {MODEL_NAME} using built-in script...")
        # Bash script usage: ./download-ggml-model.sh bases.en
        # The script downloads to the directory it is run in? or takes arg?
        # Usually it downloads to models/ in whisper.cpp root.
        
        # We will symlink or move it later.
        # Ideally we run it from WHISPER_DIR
        
        # The script argument is usually just the model name part (base.en)
        short_name = "base.en"
        
        run_cmd(["bash", "./models/download-ggml-model.sh", short_name], cwd=WHISPER_DIR)
        
        # Move it to our local models dir
        src_model = WHISPER_DIR / "models" / MODEL_NAME
        if src_model.exists():
            shutil.copy(src_model, MODEL_PATH)
            print(f"✔ Model downloaded and copied to {MODEL_PATH}")
        else:
            print("ERROR: Model download seemed to run but file not found.")
            sys.exit(1)
            
    else:
        print(f"✔ Model found at {MODEL_PATH}")

def validate_setup(exe_path):
    print("--- 4. Validating Setup ---")
    
    # Run a quick help check
    run_cmd([str(exe_path), "--help"], check=False)
    
    # Ideally run a small inference if we had a sample
    # For now, just confirming the binary calls the help menu implies it runs (isn't broken arch)
    
    print("\n--- Setup Complete ---")
    print(f"Whisper Directory: {WHISPER_DIR.resolve()}")
    print(f"Executable: {exe_path.resolve()}")
    print(f"Model Path: {MODEL_PATH.resolve()}")
    print("You can now proceed to update settings.")

def main():
    print("Humanity: Automated STT Setup (whisper.cpp)\n")
    check_dependencies()
    exe_path = setup_whisper()
    setup_model()
    validate_setup(exe_path)

if __name__ == "__main__":
    main()
