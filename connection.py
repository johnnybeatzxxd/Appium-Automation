import time
import subprocess
from geelark_api import start_phone, get_phone_status, get_adb_information

def make_phone_ready(phone_id: str) -> dict:
    """
    Makes a phone ready for use by starting it and waiting for it to be fully started.
    Then retrieves and returns the ADB connection information.
    
    Args:
        phone_id (str): The ID of the phone to start
        
    Returns:
        dict: ADB connection information for the phone, or empty dict if failed
        
    Example return format:
    {
        "ip": str,        # Connection IP
        "port": str,      # Connection port
        "pwd": str        # Connection password
    }
    """
    # Start the phone
    start_response = start_phone([phone_id])
    if not start_response or start_response.get("code") != 0:
        print(f"Failed to start phone {phone_id}")
        return {}
    
    print(f"Starting phone {phone_id}...")
    
    # Wait for phone to be fully started
    while True:
        status_info = get_phone_status([phone_id])
        
        # Check if we got any successful status information
        success_details = status_info.get("successDetails", [])
        if not success_details:
            print("Failed to get phone status")
            return {}
            
        phone_status = success_details[0]
        
        # Status codes: 0=Started, 1=Starting, 2=Shut down, 3=Expired
        if phone_status["status"] == 0:  # Phone is started
            print(f"Phone {phone_id} is now started")
            break
        elif phone_status["status"] in [2, 3]:  # Phone is shut down or expired
            print(f"Phone {phone_id} is not available (status: {phone_status['status']})")
            return {}
            
        print("Waiting for phone to start...")
        time.sleep(3)
    
    # Get ADB information
    adb_info = get_adb_information([phone_id])
    if not adb_info:
        print("Failed to get ADB information")
        return {}
        
    # Check if we got valid ADB information
    if adb_info[0].get("code") != 0:
        print("ADB information not ready yet")
        return {}
        
    connection_info = adb_info[0]
    print("\nADB Connection Information:")
    print(f"IP: {connection_info['ip']}")
    print(f"Port: {connection_info['port']}")
    print(f"Password: {connection_info['pwd']}")
    
    return connection_info

def connect_to_phone(phone_id: str) -> dict:
    """
    Connects to a phone using ADB commands.
    First makes the phone ready, then establishes ADB connection and logs in.
    
    Args:
        phone_id (str): The ID of the phone to connect to
        
    Returns:
        dict: Connection information if successful, empty dict if failed
    """
    # First make sure the phone is ready
    connection_info = make_phone_ready(phone_id)
    if not connection_info:
        print("Failed to get connection information")
        return {}
    
    # Construct the connection address
    connection_address = f"{connection_info['ip']}:{connection_info['port']}"
    
    try:
        # Connect to the phone
        print(f"\nConnecting to {connection_address}...")
        connect_cmd = ["adb", "connect", connection_address]
        connect_result = subprocess.run(connect_cmd, capture_output=True, text=True)
        
        if "connected" not in connect_result.stdout.lower():
            print(f"Failed to connect: {connect_result.stdout}")
            return {}
            
        print("Successfully connected to device")
        
        # Login to the phone
        print("Logging in...")
        login_cmd = ["adb", "-s", connection_address, "shell", "glogin", connection_info['pwd']]
        login_result = subprocess.run(login_cmd, capture_output=True, text=True)
        
        if login_result.returncode != 0:
            print(f"Failed to login: {login_result.stderr}")
            return {}
            
        print("Successfully logged in")
        return connection_info
        
    except subprocess.SubprocessError as e:
        print(f"Error executing ADB commands: {str(e)}")
        return {}
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {}

if __name__ == "__main__":
    # Example usage
    phone_id = "your_phone_id_here"
    connection_info = connect_to_phone(phone_id)
    if connection_info:
        print("Phone is ready for use!")
    else:
        print("Failed to connect to phone")
