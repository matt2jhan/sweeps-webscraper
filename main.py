import pandas as pd
from curl_cffi import requests

# Load Excel file
excel_path = 'monitoringlinks.xlsx' # Whatever the Excel file is called
df = pd.read_excel(excel_path)


# Check for URL column
if 'URL' not in df.columns:
    raise ValueError("Expected a column named URL in the sheet.")


# Loop through each link in the URL column
for index, row in df.iterrows():
    url = row['URL']
    company_name = row['Company']
    url_type = row['URL Type']

    print(f"\nAccessing ({company_name}, {url_type}): {url}")

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
            print(f"Success: {company_name}")
            # Parse response.text here
            # Now we can start scraping the site
        else:
            print(f"Failure: Status code {response.status_code}")
            print(response.text[:300])
            break # Or retry/skip

    except Exception as error:
        print(f" Failed to fetch {url}: {error}")
