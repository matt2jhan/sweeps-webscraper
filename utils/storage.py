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

    # 1️⃣ Get latest commit SHA of branch
    branch_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/ref/heads/{GITHUB_BRANCH}"
    branch_resp = requests.get(branch_url, headers=headers).json()
    latest_commit_sha = branch_resp["object"]["sha"]

    # 2️⃣ Get the tree SHA of latest commit
    commit_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits/{latest_commit_sha}"
    commit_resp = requests.get(commit_url, headers=headers).json()
    base_tree_sha = commit_resp["tree"]["sha"]

    # 3️⃣ Create blobs for each updated file
    blobs = []
    for file_path in UPDATED_FILES:
        file_name = os.path.basename(file_path)
        with open(file_path, "r") as f:
            content = f.read()

        blob_resp = requests.post(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/blobs",
            headers=headers,
            json={"content": content, "encoding": "utf-8"}
        ).json()

        blobs.append({
            "path": f"data/snapshots/{file_name}",
            "mode": "100644",
            "type": "blob",
            "sha": blob_resp["sha"]
        })

    # 4️⃣ Create new tree
    tree_resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees",
        headers=headers,
        json={"base_tree": base_tree_sha, "tree": blobs}
    ).json()
    new_tree_sha = tree_resp["sha"]

    # 5️⃣ Create commit
    commit_resp = requests.post(
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits",
        headers=headers,
        json={
            "message": "snapshots: bulk update",
            "tree": new_tree_sha,
            "parents": [latest_commit_sha]
        }
    ).json()
    new_commit_sha = commit_resp["sha"]

    # 6️⃣ Update branch reference
    update_resp = requests.patch(
        branch_url,
        headers=headers,
        json={"sha": new_commit_sha}
    )

    UPDATED_FILES.clear()
    print("🚀 Bulk snapshots push complete (multi-file commit).")