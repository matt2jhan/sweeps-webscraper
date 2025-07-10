from playwright.sync_api import sync_playwright
import pandas as pd
import time, random

# Load Excel file
excel_path = 'monitoringlinks.xlsx' # Whatever the Excel file is called
df = pd.read_excel(excel_path)


# Check for URL column
if 'URL' not in df.columns:
    raise ValueError("Expected a column named URL in the sheet.")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False) # Open browser
    context = browser.new_context() # Open window
    page = context.new_page() # Open tab
 
 
 
    # Loop through each link in the URL column
    for index, row in df.iterrows():
        url = row['URL']
        company_name = row['Company']
        url_type = row['URL Type']
        try:
            print(f"\nAccessing ({company_name}, {url_type}): {url}")
            time.sleep(random.uniform(2, 5))
            response = page.goto(url, timeout=30000)
            if response.status == 200:
                print(f"Success: {company_name}")
                # Here we start scraping the site
            else:
                print(f"Failure: Status code {response.status}")
                print(page.content())

        except Exception as error:
            print(f" Failed to fetch {url}: {error}")
    browser.close()
