#!/bin/bash
set -e

rm -rf build
rm -rf dist
rm -rf pkgroot

pyinstaller --windowed --noconfirm --clean \
  --name "Cloudflare DNS Manager" \
  --icon Cloudflare32px.icns \
  --add-data "Cloudflare32px.png:." \
  --add-data "Cloudflare32px_gray.png:." \
  kivyapp.py

rm -rf pkgroot/Applications/Cloudflare\ DNS\ Manager.app
mkdir -p pkgroot/Applications
cp -R "dist/Cloudflare DNS Manager.app" pkgroot/Applications/

pkgbuild --root pkgroot --install-location / --identifier com.cloudflare.dnsmanager --version 1.0 CloudflareDNSManager.pkg

echo "Done! .pkg installer: CloudflareDNSManager.pkg" 
