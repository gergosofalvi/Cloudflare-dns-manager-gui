# 1. Buildeld ki az appot (ez már megvan)
# dist/Cloudflare DNS Manager.app

# 2. Készíts egy ideiglenes mappát
mkdir -p installer_dmg

# 3. Másold bele az appot
cp -R "dist/Cloudflare DNS Manager.app" installer_dmg/

# 4. Készíts Applications alias-t
ln -s /Applications installer_dmg/Applications

# 5. Készítsd el a DMG-t
hdiutil create -volname "Cloudflare DNS Manager" -srcfolder installer_dmg -ov -format UDZO CloudflareDNSManager.dmg