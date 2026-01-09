import requests
from bs4 import BeautifulSoup
from pathlib import Path
import os
import sys

# Config
BASE_URL = "http://127.0.0.1:5000"
FILE_PATH = Path("data/sample_transactions.csv")

def verify_upload():
    if not FILE_PATH.exists():
        print(f"Error: File not found at {FILE_PATH.absolute()}")
        sys.exit(1)

    session = requests.Session()
    upload_url = f"{BASE_URL}/upload"
    
    print(f"Attempting to upload {FILE_PATH} to {upload_url}")

    # 1. GET request to fetch CSRF token (and likely render page)
    # Even if using AJAX, we might need CSRF token from the page meta or form
    try:
        response = session.get(upload_url)
        if response.status_code != 200:
            print(f"Failed to load upload page. Status: {response.status_code}")
            sys.exit(1)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        
        data = {}
        if csrf_token:
            data['csrf_token'] = csrf_token['value']
            print(f"CSRF token found: {csrf_token['value'][:10]}...")
        else:
            # Maybe it's in meta tag
            meta_csrf = soup.find('meta', {'name': 'csrf-token'})
            if meta_csrf:
                data['csrf_token'] = meta_csrf['content']
                print("CSRF token found in meta tag.")
            else:
                print("No CSRF token found in form or meta.")

        # 2. POST request to /upload/process
        process_url = f"{BASE_URL}/upload/process"
        print(f"Uploading to {process_url}...")
        
        # Check input name again, assume 'file' is correct based on upload.py code:
        # file = request.files['file']
        
        with open(FILE_PATH, 'rb') as f:
            files = {'file': f}
            # Flask-WTF CSRF checks token in data or headers.
            # If standard form submit, data is fine.
            response = session.post(process_url, files=files, data=data)
        
        print(f"Upload Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Upload successful!")
            try:
                json_resp = response.json()
                print("Response JSON:", json_resp)
                if json_resp.get('success'):
                    print("Server reported success.")
                else:
                    print("Server reported failure in JSON.")
            except:
                print("Response text:", response.text[:200])
        else:
            print(f"Upload failed with status {response.status_code}")
            print("Response:", response.text[:200])

        # 3. Verify data by checking transactions page
        print("Verifying transactions...")
        trans_url = f"{BASE_URL}/transactions"
        r_trans = session.get(trans_url)
        # Check for some known content from sample csv
        # sample_transactions.csv content is unknown but let's assume it has data
        if "table" in r_trans.text:
             print("Transactions page loaded, table found.")
        else:
             print("Transactions page loaded but table not found?")
            
    except Exception as e:
        print(f"Exception happened: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_upload()
