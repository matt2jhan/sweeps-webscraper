import pandas as pd
from curl_cffi import requests
from flask import Flask, render_template, request
import os

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
            # Session Headers - fake browser info
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }

            response = requests.get(
                url, 
                timeout=30, 
                impersonate="chrome120", # Could replace with safari/firefox if bugging
                headers=headers,
            )

            if response.status_code == 200:
                results += f"Success: {company_name}\n"
                # Parse response.text here
                # Now we can start scraping the site
            else:
                results += f"Failure: Status code {response.status_code}\n"
                print(response.text[:300])
                break # Or retry/skip

        except Exception as error:
            results += f" Failed to fetch {url}: {error}\n"

    return render_template('index.html', results=results)

if __name__ == "__main__":
    app.run(debug=True) # Remember to use flask run later