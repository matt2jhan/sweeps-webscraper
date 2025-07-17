from curl_cffi import requests

try:
    response = requests.get(
        "https://www.autolus.com/investor-relations-media/news-media/",
        impersonate="chrome120",  # You can try chrome120, firefox118, safari16_0
        timeout=30,
    )

    if response.status_code == 200:
        print("Success!")
        print(response.text[:1000])  # Print first 1000 characters
    else:
        print(f"Failed: Status code {response.status_code}")
        print(response.text[:500])

except requests.RequestException as e:
    print(f"Request failed: {e}")
