# Cloudflare DNS Manager

A native macOS application for managing multiple Cloudflare accounts, domains, and DNS records, built with Kivy and KivyMD.
DEV

## Features

- Manage multiple Cloudflare accounts (API tokens and custom labels)
- View and search all domains (zones) across all accounts
- Add, edit, and delete DNS records with a user-friendly interface
- Search/filter DNS records by name and content
- Autocomplete domain selector with instant filtering
- Save and restore window size and position
- Native macOS look and feel, with custom icons and images
- All resources (icons, images) are bundled in the app and installer
- One-file app bundle and .pkg installer for easy distribution

## Screenshots

*(Add your screenshots here)*

## Requirements

- Python 3.9+
- macOS (tested on Apple Silicon and Intel)
- See `requirements.txt` for Python dependencies

## Installation

### 1. Clone the repository

```sh
git clone https://github.com/yourusername/cloudflare-dns-manager-ui.git
cd cloudflare-dns-manager-ui
```

### 2. Create a virtual environment and install dependencies

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the app in development mode

```sh
python kivyapp.py
```

### 4. Build the standalone macOS app and .pkg installer

The project includes a build script and PyInstaller spec file to create a native `.app` bundle and a `.pkg` installer.

```sh
bash builder.sh
```

- The `.app` bundle will be in `dist/Cloudflare DNS Manager.app`
- The installer will be `CloudflareDNSManager.pkg`

## Usage

- On first launch, add your Cloudflare account(s) with API token and a custom label.
- All domains (zones) from all accounts will be listed, with the account label shown.
- Use the search bar to quickly find domains or DNS records.
- Add, edit, or delete DNS records as needed.
- Window size and position are saved automatically.

## Cloudflare Account JSON Format

The app stores account information in a JSON file at:

```
~/Library/Application Support/Cloudflare DNS Manager/cloudflare_token.json
```

Example format for multiple accounts:

```json
{
  "accounts": [
    {
      "account_id": "36f111dd995486c4a432bd7ab1e9d296",
      "token": "your_cloudflare_api_token",
      "label": "Work"
    },
    {
      "account_id": "b7e1c2d3f4a5b6c7d8e9f0a1b2c3d4e5",
      "token": "another_token",
      "label": "Personal"
    }
  ],
  "window": {
    "size": [1200, 800],
    "pos": [100, 100]
  }
}
```

You can manage accounts from the app's settings popup.

## Project Structure

- `kivyapp.py` - Main application code
- `requirements.txt` - Python dependencies
- `builder.sh` - Build script for PyInstaller and pkgbuild
- `Cloudflare DNS Manager.spec` - PyInstaller spec file
- `Cloudflare32px.png`, `Cloudflare32px_gray.png` - Cloudflare proxy icons
- `Cloudflare32px.icns` - App icon for macOS
- `dist/`, `build/`, `pkgroot/` - Build output directories

## Development

- The app uses Kivy and KivyMD for the UI.
- All resources are loaded using a helper function to support both development and bundled (PyInstaller) modes.
- The app is designed for macOS, but the core logic is cross-platform.

## License

MIT License 