import pandas as pd
from curl_cffi import requests
from flask import Flask, render_template, request
import os
from utils.scraper import extract_items
from utils.storage import load_previous_snapshot, save_snapshot, detect_new_items
from utils.fetcher import fetch_html

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file"
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    excelpath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(excelpath)

    # Load Excel file
    df = pd.read_excel(excelpath)

    results = ""

    # Check for URL column
    if 'URL' not in df.columns:
        raise ValueError("Expected a column named URL in the sheet.")


    # Loop through each link in the URL column
    for index, row in df.iterrows():
        url = row['URL']
        company_name = row['Company']
        url_type = row['URL Type']

        results += f"\nAccessing ({company_name}, {url_type}): {url}\n"

        try:
            html, source, status_code = fetch_html(url)

            if html:
                results += f"Success ({source}): {company_name}\n"

                items, error = extract_items(html, url)
                if error:
                    results += f"  ⚠️ Could not extract structured content: {error}\n"
                    continue

                previous = load_previous_snapshot(company_name, url_type)
                new_items = detect_new_items(previous, items)

                if new_items:
                    results += f"  🆕 {len(new_items)} new item(s) found:\n"
                    for item in new_items:
                        results += f"    - {item['title']} ({item['timestamp']})\n"
                        results += f"      Link: {item['link']}\n"
                else:
                    results += "  ✅ No new content since last check.\n"

                save_snapshot(company_name, url_type, items)

            else:
                if status_code == 404: # Common errors
                    results += f" 🚨 Failure: Status code {status_code}. Website does not exist.\n"
                elif status_code == 403:
                    results += f" 🚨 Failure: Status code {status_code}. Forbidden (bot detected).\n"
                elif status_code:
                    results += f" 🚨 Failure: Status code {status_code}. Please check manually.\n"
                else:
                    results += f" 🚨 Failed to fetch {url}. Please check URL address. Finding: {error} \n"

        except Exception as error:
            results += f" 🚨 Failed to fetch {url} from spreadsheet: {error}\n"

    return render_template('index.html', results=results)

if __name__ == "__main__":
    app.run(debug=True) # Remember to use flask run later