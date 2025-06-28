import uuid
import time
import hashlib
import requests
import json
import os
import webbrowser
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
    """
    Start the specified cloud phones and open their URLs in the browser.
    
    Args:
        ids (list[str]): List of cloud phone IDs to start
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/start"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids":ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() 
        
        response_data = response.json()
        if response_data.get("code") == 0:
            # Open each phone's URL in the browser
            success_details = response_data.get("data", {}).get("successDetails", [])
            for phone in success_details:
                url = phone.get("url")
                if url:
                    print(f"Opening phone {phone.get('id')} in browser...")
                    webbrowser.open(url)
                    time.sleep(1)  # Small delay between opening multiple URLs
        return response_data
        
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")
        return None

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

def get_adb_information(ids: list[str]) -> dict:
    """
    Get ADB connection information for specified cloud phones.
    
    Args:
        ids (list[str]): List of cloud phone IDs to get ADB information for
        
    Returns:
        dict: Response containing ADB connection details for each phone
        
    Response format:
    {
        "items": [
            {
                "code": int,      # 0 for success, other codes indicate errors
                "id": str,        # Cloud phone ID
                "ip": str,        # Connection IP
                "port": str,      # Connection port
                "pwd": str        # Connection password
            },
            ...
        ]
    }
    """
    api_url = "https://openapi.geelark.com/open/v1/adb/getData"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        response_data = response.json()
        if response_data.get("code") == 0:
            return response_data.get("data", {}).get("items", [])
        else:
            print(f"API Error: {response_data.get('msg')}")
            return []
            
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")
        return []
    except Exception as e:
        print(f"Error getting ADB information: {str(e)}")
        return []

def get_available_phones(adb_enabled=True) -> list[dict]:
    """
    Get a list of available phones based on their remark field.
    Phones are considered available if their remark doesn't contain 'inactive'.
    
    Returns:
        list[dict]: List of available phones with their details
    """
    # Get all phones
    phones = get_all_cloud_phones()
    
    if not phones:
        return []
    
    # Filter and format available phones
    available_phones = []
    for phone in phones:
        remark = phone.get("remark", "").lower()
        if "inactive" not in remark:
            equipment_info = phone.get("equipmentInfo", {})
            phone_info = {
                "id": phone.get("id"),
                "name": phone.get("serialName", "Unknown"),
                "status": "active",
                "brand": equipment_info.get("deviceBrand", "Unknown"),
                "model": equipment_info.get("deviceModel", "Unknown")
            }
            available_phones.append(phone_info)
    
    # Get ADB info for available phones
    phone_ids = [phone["id"] for phone in available_phones]
    adb_info = get_adb_information(phone_ids)
    if adb_enabled:    
        # Filter out phones where ADB is not enabled (code 49001)
        return [phone for phone in available_phones 
                if not any(adb["id"] == phone["id"] and adb["code"] == 49001 for adb in adb_info)]
    return available_phones

def get_phone_status(ids: list[str]) -> dict:
    """
    Query the status of cloud phones by their IDs.
    
    Args:
        ids (list[str]): List of cloud phone IDs to query status for (max 100 elements)
        
    Returns:
        dict: Response containing status details for each phone
        
    Response format:
    {
        "totalAmount": int,      # Total number of requested IDs
        "successAmount": int,    # Number of successful responses
        "failAmount": int,       # Number of failed responses
        "successDetails": [      # List of successful phone statuses
            {
                "id": str,           # Phone ID
                "serialName": str,   # Phone name
                "status": int        # Status code (0=Started, 1=Starting, 2=Shut down, 3=Expired)
            }
        ],
        "failDetails": [         # List of failed queries
            {
                "code": int,     # Error code
                "id": str,       # Phone ID
                "msg": str       # Error message
            }
        ]
    }
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/status"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        
        response_data = response.json()
        if response_data.get("code") == 0:
            return response_data.get("data", {})
        else:
            print(f"API Error: {response_data.get('msg')}")
            return {}
            
    except requests.exceptions.HTTPError as errh:
        print(f"Http Error: {errh}")
        print(f"Response code: {response.status_code}")
        return {}
    except Exception as e:
        print(f"Error getting phone status: {str(e)}")
        return {}

if __name__ == '__main__':
    print("Getting available phones (excluding those with ADB not enabled)...")
    available_phones = get_available_phones()
    print("\nAvailable phones:")
    print(json.dumps(available_phones, indent=4))



