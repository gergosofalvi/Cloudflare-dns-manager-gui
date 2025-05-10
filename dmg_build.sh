#!/bin/bash
set -e

# 1. Verzió beállítása (ha van GITHUB_REF vagy argumentum)
if [ -n "$GITHUB_REF" ]; then
  VERSION=${GITHUB_REF#refs/tags/}
elif [ -n "$1" ]; then
  VERSION="$1"
else
  VERSION="dev"
fi

echo "$VERSION" > version.txt
sed -i '' "s/^APP_VERSION = .*/APP_VERSION = \"$VERSION\"/" kivyapp.py

echo "Building app..."
pyinstaller --windowed --noconfirm --clean \
  --name "Cloudflare DNS Manager" \
  --icon Cloudflare32px.icns \
  --add-data "Cloudflare32px.png:." \
  --add-data "Cloudflare32px_gray.png:." \
  kivyapp.py

# 2. DMG mappa előkészítése
rm -rf installer_dmg
mkdir -p installer_dmg
cp -R "dist/Cloudflare DNS Manager.app" installer_dmg/
ln -s /Applications installer_dmg/Applications

# 3. DMG készítése (create-dmg vagy hdiutil fallback)
if command -v create-dmg >/dev/null 2>&1; then
  create-dmg \
    --volname "Cloudflare DNS Manager" \
    --window-size 500 300 \
    --icon-size 120 \
    --icon "Cloudflare DNS Manager.app" 100 120 \
    --icon "Applications" 380 120 \
    --app-drop-link 380 120 \
    CloudflareDNSManager.dmg \
    installer_dmg/
else
  echo "create-dmg not found, using hdiutil fallback"
  hdiutil create -volname "Cloudflare DNS Manager" -srcfolder installer_dmg -ov -format UDZO CloudflareDNSManager.dmg
fi

# 4. Feltöltés (ha van UPLOAD_KEY)
if [ -n "$UPLOAD_KEY" ]; then
  echo "Uploading DMG..."
  curl -X POST https://cfdnsmanager.geri.app/upload \
    -F "key=$UPLOAD_KEY" \
    -F "version=$VERSION" \
    -F "dmg=@CloudflareDNSManager.dmg"
else
  echo "UPLOAD_KEY not set, skipping upload."
fi

echo "DMG build script finished."