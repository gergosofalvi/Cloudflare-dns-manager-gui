import os
import json
from flask import Flask, request, send_from_directory, jsonify

app = Flask(__name__)
UPLOAD_KEY = os.environ.get('UPLOAD_KEY', 'your_upload_key')
DATA_DIR = '/app/data'
UPDATE_JSON = os.path.join(DATA_DIR, 'update.json')

@app.route('/update.json', methods=['GET'])
def get_update():
    if os.path.exists(UPDATE_JSON):
        return send_from_directory(DATA_DIR, 'update.json')
    return jsonify({'error': 'update.json not found'}), 404

@app.route('/upload', methods=['POST'])
def upload_dmg():
    key = request.form.get('key')
    version = request.form.get('version')
    dmg_file = request.files.get('dmg')
    if key != UPLOAD_KEY:
        return jsonify({'error': 'Invalid key'}), 403
    if not dmg_file or not version:
        return jsonify({'error': 'Missing file or version'}), 400
    version_folder = f'release/{version}'
    version_dir = os.path.join(DATA_DIR, version_folder)
    os.makedirs(version_dir, exist_ok=True)
    dmg_filename = 'CloudflareDNSManager.dmg'
    dmg_path = os.path.join(version_dir, dmg_filename)
    dmg_file.save(dmg_path)
    # latest szimlink frissítése
    latest_dir = os.path.join(DATA_DIR, 'release', 'latest')
    os.makedirs(latest_dir, exist_ok=True)
    latest_dmg = os.path.join(latest_dir, dmg_filename)
    if os.path.islink(latest_dmg) or os.path.exists(latest_dmg):
        os.remove(latest_dmg)
    os.symlink(os.path.relpath(dmg_path, latest_dir), latest_dmg)
    update_data = {
        'version': version,
        'dmg_url': f'https://cfdnsmanager.geri.app/app/osx/{version_folder}/CloudflareDNSManager.dmg'
    }
    with open(UPDATE_JSON, 'w') as f:
        json.dump(update_data, f)
    return jsonify({'success': True, 'update': update_data})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000) 