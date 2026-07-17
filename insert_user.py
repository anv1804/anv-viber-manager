import requests
import hashlib
import uuid

url = "https://hqbsupczeujqgrkvrdjx.supabase.co/rest/v1/users"
key = "sb_publishable_249FmOz7LjCvA6-dAlTHkg_mngyhFt9"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

hashed_pass = hashlib.sha256("18042004@nV".encode()).hexdigest()
user_id = str(uuid.uuid4())

# We will try to insert status: active and role: admin (just in case they have role column)
payload = {
    "id": user_id,
    "username": "anv184",
    "password_hash": hashed_pass,
    "status": "active",
    "role": "admin"
}

print("Payload:", payload)
resp = requests.post(url, headers=headers, json=payload)
print("Status Code:", resp.status_code)
print("Response:", resp.text)

# If it failed due to 'role' column not existing, retry without 'role'
if resp.status_code != 201:
    print("Retrying without 'role' column...")
    payload.pop("role", None)
    resp = requests.post(url, headers=headers, json=payload)
    print("Retry Status Code:", resp.status_code)
    print("Retry Response:", resp.text)
