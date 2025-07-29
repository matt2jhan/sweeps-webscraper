# To store the data about a site
import os
import json
import hashlib
import base64
import requests

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
    path = get_snapshot_path(company_name, url_type)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
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
    if not UPDATED_FILES:
        print("✅ No snapshots to push.")
        return
    
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    for file_path in UPDATED_FILES:
        file_name = os.path.basename(file_path)
        api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/data/snapshots/{file_name}"

        with open(file_path, "rb") as f:
            content = f.read()
        encoded_content = base64.b64encode(content).decode("utf-8")

        # Check if file exists
        response = requests.get(api_url, headers=headers)
        sha = response.json().get("sha") if response.status_code == 200 else None

        commit_data = {
            "message": "snapshots: bulk update",
            "content": encoded_content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            commit_data["sha"] = sha

        put_response = requests.put(api_url, headers=headers, json=commit_data)
        if put_response.status_code not in [200, 201]:
            print(f"❌ Failed: {file_name} - {put_response.text}")
        else:
            print(f"✅ Pushed {file_name}")

    UPDATED_FILES.clear()
    print("🚀 Bulk snapshots push complete.")