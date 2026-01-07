#!/bin/bash
set -e

echo "🚀 Starting Humanity Build Pipeline..."

# 0. Cleanup
echo "🧹 Cleaning previous builds..."
rm -rf dist build web/out web/dist
rm -rf web/backend  # Clean old backend copy

# 1. Build Python Backend
echo "🐍 Building Python Backend..."
# Ensure dependencies are installed (already done in dev, but listed here for clarity)
# pip install -r requirements.txt
# pip install pyinstaller

# Run PyInstaller
./venv/bin/pyinstaller backend.spec --clean --noconfirm

# Verify binary exists
if [ ! -f "dist/humanity-backend" ]; then
    echo "❌ Backend build failed: Binary not found."
    exit 1
fi
echo "✅ Backend built successfully."


# 2. Build Frontend (Next.js)
echo "⚛️  Building Next.js Frontend..."
cd web
npm install
npm run build
cd ..

# 3. Prepare Electron Resources
echo "📦 Preparing Electron Resources..."
# Electron Builder expects resources in specific places or configured in package.json
# We want to bundle the 'dist/humanity-backend' folder into the Electron app.
# We'll copy it to 'web/backend' so it's inside the electron root for easy packaging config
mkdir -p web/backend
cp dist/humanity-backend web/backend/

# 4. Package Electron App
echo "💿 Packaging Electron App..."
cd web
npm run electron:build
cd ..

echo "🎉 Build Complete! Artifacts in web/dist/"
