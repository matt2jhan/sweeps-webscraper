# To access a site
import cloudscraper
from curl_cffi import requests

def fetch_html(url):
    # Session Headers - fake browser info
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        # Try curl_cffi first
        response = requests.get(
            url, 
            timeout=10, 
            impersonate="chrome120", # Could replace with safari/firefox if bugging
            headers=headers
        )
    
        if response.status_code == 200 and "Just a moment" not in response.text:
            return response.text, "curl_cffi", response.status_code
        
    except Exception:
        pass

    try:
        # Fallback: use cloudscraper if bot-detected or failed
        scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome", 
                "platform": "windows", 
                "mobile": False
            }
        )

        response = scraper.get(
            url, 
            timeout=30
        )

        if response.status_code == 200:
            return response.text, "cloudscraper", response.status_code
        else:
            return None, "cloudscraper", response.status_code
        
    except Exception as e:
        return None, f"Failed to fetch via cloudscraper: {e}", None
