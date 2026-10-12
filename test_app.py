import requests
import sqlite3
import pyotp
import os
import re

BASE_URL = 'https://127.0.0.1:5000'
DB_PATH = 'instance/database.db'

# Disable insecure request warnings for self-signed certs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def run_tests():
    s = requests.Session()
    s.verify = False
    
    print("Testing Home Redirect...")
    r = s.get(f'{BASE_URL}/', allow_redirects=False)
    print(f"Home redirect status: {r.status_code}")
    
    print("\nTesting Registration...")
    # Get CSRF token if needed
    r_reg_get = s.get(f'{BASE_URL}/auth/register')
    # Find CSRF token
    csrf_token = ''
    match = re.search(r'name="csrf_token" value="([^"]+)"', r_reg_get.text)
    if match:
        csrf_token = match.group(1)
        
    import time
    username = f"tester_{int(time.time())}"
    email = f"{username}@example.com"
    data = {
        'csrf_token': csrf_token,
        'username': username,
        'email': email,
        'password': 'Password123!'
    }
    r_reg = s.post(f'{BASE_URL}/auth/register', data=data)
    print(f"Register POST status: {r_reg.status_code}")
    
    # Get 2FA secret from DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT twofa_secret FROM user WHERE email='{email}'")
    row = cursor.fetchone()
    if not row:
        print("User not found in DB!")
        return
    secret = row[0]
    conn.close()
    
    print("\nTesting 2FA Setup...")
    totp = pyotp.TOTP(secret)
    code = totp.now()
    
    match = re.search(r'name="csrf_token" value="([^"]+)"', r_reg.text)
    if match:
        csrf_token = match.group(1)
        
    data = {
        'csrf_token': csrf_token,
        'code': code
    }
    r_2fa = s.post(f'{BASE_URL}/auth/setup-2fa', data=data, allow_redirects=False)
    print(f"2FA Setup POST status: {r_2fa.status_code}")
    if r_2fa.status_code == 302:
        print(f"Redirects to: {r_2fa.headers.get('Location')}")
        
    print("\nTesting Dashboard...")
    r_dash = s.get(f'{BASE_URL}/docs/dashboard')
    print(f"Dashboard status: {r_dash.status_code}")
    if username in r_dash.text:
        print("Dashboard loaded successfully.")
    else:
        print("Dashboard failed or user not shown.")
        
    print("\nTesting Upload Page...")
    r_upload_get = s.get(f'{BASE_URL}/docs/upload')
    print(f"Upload GET status: {r_upload_get.status_code}")
    
    match = re.search(r'name="csrf_token" value="([^"]+)"', r_upload_get.text)
    if match:
        csrf_token = match.group(1)
        
    with open('test_doc.txt', 'w') as f:
        f.write('This is a test document.')
        
    with open('test_doc.txt', 'rb') as f:
        files = {'file': ('test_doc.txt', f, 'text/plain')}
        data = {'csrf_token': csrf_token}
        r_upload_post = s.post(f'{BASE_URL}/docs/upload', data=data, files=files, allow_redirects=False)
    
    print(f"Upload POST status: {r_upload_post.status_code}")
    if r_upload_post.status_code == 302:
        print(f"Redirects to: {r_upload_post.headers.get('Location')}")
    
if __name__ == '__main__':
    run_tests()
