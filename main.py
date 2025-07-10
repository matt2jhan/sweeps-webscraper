import requests
import pandas as pd

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
    try:
        print(f"\nAccessing ({company_name}, {url_type}): {url}")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"Success: {url}")
        else:
            print(f"Failed with status code: {response.status_code}")
            print({response.text[:1000]})
    except requests.exceptions.RequestExeption as error:
        print(f"Error accessing {url}: {error}")

