import requests

url = "https://hqbsupczeujqgrkvrdjx.supabase.co/rest/v1/users?username=eq.anv184"
key = "sb_publishable_249FmOz7LjCvA6-dAlTHkg_mngyhFt9"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

resp = requests.patch(url, json={"role": "admin"}, headers=headers)
print("Status Code:", resp.status_code)
print("Response:", resp.text)
