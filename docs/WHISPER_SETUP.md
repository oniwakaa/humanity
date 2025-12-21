# Environment Setup: whisper.cpp STT

This guide describes how to set up the local development environment for the Speech-to-Text (STT) subsystem using `whisper.cpp`.

## Prerequisites (macOS)
Ensure the following system tools are installed:
- **Git** (`git`)
- **Make** (`make`)
- **C/C++ Compiler** (clang via Xcode Command Line Tools)
- **Python 3.11** (for the orchestration script)

To install missing dependencies on macOS:
```bash
xcode-select --install
```

## Setup Instructions

### Option A: Automated Setup (Recommended)
This project includes a Python script to automate the build and model download process.

1. **Run the Setup Script**
   ```bash
   python scripts/setup_whisper.py
   ```
   This script will:
   - Clone `whisper.cpp` into `./vendor/whisper.cpp`
   - Build the `main` executable using `make`
   - Download the `base.en` model (if missing) to `./models/ggml-base.en.bin`
   - Validate the installation

### Option B: Manual Setup
If you prefer to set up manually, follow these steps:

1. **Clone Repository**
   ```bash
   mkdir -p vendor
   cd vendor
   git clone https://github.com/ggerganov/whisper.cpp.git
   cd whisper.cpp
   ```

2. **Build**
   ```bash
   make
   # Verify output
   ./main --help
   ```

3. **Get the Model**
   Download the `ggml-base.en.bin` model.
   ```bash
   bash ./models/download-ggml-model.sh base.en
   ```
   *Note: This downloads to `vendor/whisper.cpp/models/`*

4. **Configure Project**
   Move or symlink the model to the project `models/` directory.
   ```bash
   cd ../..
   mkdir -p models
   cp vendor/whisper.cpp/models/ggml-base.en.bin models/
   ```

## Configuration

Update your project settings to point to the local resources.

**Path References:**
- `WHISPER_CPP_DIR`: `./vendor/whisper.cpp`
- `WHISPER_MODEL_PATH`: `./models/ggml-base.en.bin`

## Validation Checks
To verify the setup is working correctly:

1. **Check Binary**: Run `./vendor/whisper.cpp/main -h` to ensure it executes without error.
2. **Check Model**: Ensure `models/ggml-base.en.bin` is approx 148MB.
3. **Run Test**:
   ```bash
   ./vendor/whisper.cpp/main -m models/ggml-base.en.bin -f samples/jfk.wav
   ```
   *(Note: You supply your own sample audio if `samples/jfk.wav` is missing from the clone, though it is usually included in the repo.)*

## Troubleshooting

### Build Failures
- **Error**: `make: command not found`
  - **Fix**: Install Xcode Command Line Tools (`xcode-select --install`).
- **Error**: `fatal error: 'stdio.h' file not found`
  - **Fix**: Reinstall/reset Xcode tools.

### Model Issues
- **Error**: `invalid model file` or `failed to load model`
  - **Fix**: Verify file size. Re-download using the script. Ensure you are using a `.bin` file compatible with the checked-out version of whisper.cpp.

### Audio Capture
- **Issue**: Backend cannot access microphone.
  - **Fix**: On macOS, Terminal/VSCode needs permission to access the Microphone. Check System Settings > Privacy & Security > Microphone.
