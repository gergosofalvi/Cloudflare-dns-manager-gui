#!/bin/bash
set -e

# Verzió APP_VERSION.txt-ből
if [ -f APP_VERSION.txt ]; then
  VERSION=$(cat APP_VERSION.txt)
else
  VERSION="0.0.0"
fi

pyinstaller --windowed --noconfirm --clean \
  --name "Cloudflare DNS Manager" \
  --icon Cloudflare32px.icns \
  --add-data "Cloudflare32px.png:." \
  --add-data "Cloudflare32px_gray.png:." \
  kivyapp.py

rm -rf pkgroot/Applications/Cloudflare\ DNS\ Manager.app
mkdir -p pkgroot/Applications
cp -R "dist/Cloudflare DNS Manager.app" pkgroot/Applications/

PKG_NAME="CloudflareDNSManager_${VERSION}.pkg"
pkgbuild --root pkgroot --install-location / --identifier com.cloudflare.dnsmanager --version "$VERSION" "$PKG_NAME"

echo "Done! .pkg installer: $PKG_NAME" 
