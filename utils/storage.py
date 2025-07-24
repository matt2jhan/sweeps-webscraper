import os
import json

SNAPSHOT_DIR = os.path.join('data', 'snapshots')

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

def detect_new_items(previous, current):
    prev_titles = set(item['title'] for item in previous)
    return [item for item in current if item['title'] not in prev_titles]
