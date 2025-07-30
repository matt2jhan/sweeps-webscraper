# To store the data about a site
import os
import json
import hashlib
import base64
import requests
import zipfile
from io import BytesIO

SNAPSHOT_DIR = os.path.join('data', 'snapshots')
UPDATED_FILES = set()
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")

try:
    from streamlit.runtime.secrets import secrets
    GITHUB_TOKEN = secrets["GITHUB_TOKEN"]
except:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_snapshot_path(company_name, url_type):
    safe_name = f"{company_name}_{url_type}".replace(" ", "_")
    return os.path.join(SNAPSHOT_DIR, f"{safe_name}.json")

def load_previous_snapshot(company_name, url_type):
    safe_name = f"{company_name}_{url_type}".replace(" ", "_") + ".json"
    
    zip_path = os.path.join(SNAPSHOT_DIR, "snapshots.zip")

    # --- If running locally and ZIP exists ---
    if os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, "r") as zipf:
            if safe_name in zipf.namelist():
                with zipf.open(safe_name) as f:
                    return json.load(f)
        return []
    
    # --- If on Streamlit Cloud (pull latest from GitHub) ---
    try:
        zip_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/snapshots.zip"
        r = requests.get(zip_url)
        if r.status_code == 200:
            with zipfile.ZipFile(BytesIO(r.content)) as zipf:
                if safe_name in zipf.namelist():
                    with zipf.open(safe_name) as f:
                        return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load from ZIP: {e}")
    
    return []

def save_snapshot(company_name, url_type, data):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    path = get_snapshot_path(company_name, url_type)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    UPDATED_FILES.add(path)

def hash_item(item):
    data = f"{item.get('title','')}|{item.get('timestamp','')}|{item.get('link','')}"
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def detect_new_items(previous, current):
    prev_hashes = set(hash_item(item) for item in previous)
    return [item for item in current if hash_item(item) not in prev_hashes]

def push_bulk_snapshots():
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(SNAPSHOT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=file)
    zip_buffer.seek(0)

    # Encode for GitHub API
    encoded_content = base64.b64encode(zip_buffer.read()).decode("utf-8")

    # GitHub API URL for storing ZIP
    zip_filename = "snapshots.zip"
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{zip_filename}"

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(api_url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None

    commit_data = {
        "message": "Bulk snapshot update (zip)",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    if sha:
        commit_data["sha"] = sha

    put_response = requests.put(api_url, headers=headers, json=commit_data)
    if put_response.status_code not in [200, 201]:
        print(f"❌ Failed to push ZIP: {put_response.text}")
    else:
        print("✅ Bulk snapshots pushed as ZIP.")