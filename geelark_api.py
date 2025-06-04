import uuid
import time
import hashlib
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

app_id: str =  os.getenv("geelark_app_id")
api_key: str = os.getenv("geelark_api_key")

def generate_api_headers(app_id: str, api_key: str) -> dict:
    """
    Generates the required headers for the API request.

    Args:
        app_id: Your team's AppId.
        api_key: Your team's ApiKey.

    Returns:
        A dictionary containing the request headers.
    """
    trace_id = str(uuid.uuid4())
    ts = str(int(time.time() * 1000))
    nonce = trace_id[:6]

    # Concatenate the string for signature
    sign_str = app_id + trace_id + ts + nonce + api_key

    # Generate SHA256 hexadecimal uppercase digest
    sha256_hash = hashlib.sha256(sign_str.encode('utf-8')).hexdigest().upper()

    headers = {
        "Content-Type": "application/json",
        "appId": app_id,
        "traceId": trace_id,
        "ts": ts,
        "nonce": nonce,
        "sign": sha256_hash
    }
    return headers

def get_all_cloud_phones(
    page: int = None,
    page_size: int = 100,
    ids: list[str] = None,
    serial_name: str = None,
    remark: str = None,
    group_name: str = None,
    tags: list[str] = None
) -> dict:


    api_url = "https://openapi.geelark.com/open/v1/phone/list"
    
    headers = generate_api_headers(app_id, api_key)
    
    payload = {}
    if page is not None:
        payload["page"] = page
    if page_size is not None:
        payload["pageSize"] = page_size
    if ids is not None:
        payload["ids"] = ids
    if serial_name is not None:
        payload["serialName"] = serial_name
    if remark is not None: 
        payload["remark"] = remark
    if group_name is not None: 
        payload["groupName"] = group_name
    if tags is not None: 
        payload["tags"] = tags

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        
        response_data = response.json()
        return response_data["data"]["items"]
        
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")

def start_phone(ids:list[str]):

    api_url = "https://openapi.geelark.com/open/v1/phone/start"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids":ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        
        response_data = response.json()
        return response_data
        
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")

def stop_phone(ids:list[str]):
    api_url = "https://openapi.geelark.com/open/v1/phone/stop"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids":ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        
        response_data = response.json()
        return response_data
        
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")

def get_adb_information(ids:list[str]):
    
    api_url = "https://openapi.geelark.com/open/v1/adb/getData"
    headers = generate_api_headers(app_id,api_key)
    payload = {"ids":ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        
        response_data = response.json()
        return response_data
        
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")

if __name__ == '__main__':
    phones_list = get_all_cloud_phones(page=1, page_size=10)
    print("API Response:")
    print(json.dumps(phones_list, indent=4))

    phone_ids = [ phone_id.get("id") for phone_id in phones_list ]

    print("Stating the Phones ...")
    response = start_phone(phone_ids)
    print(response)

    adb_infos = get_adb_information(phone_ids)

    while adb_infos["data"]["items"][0]["code"] != 0:
        adb_infos = get_adb_information(phone_ids)
        print("nope")
        time.sleep(2)

    print("its ready")

    print("adb creds",adb_infos)



