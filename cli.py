import os
import signal
import sys
import time
import subprocess
import re
import threading
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from geelark_api import get_available_phones, stop_phone
from connection import connect_to_phone
from appium import webdriver
from appium.options.android import UiAutomator2Options
from helper import open_page
from swipe import realistic_swipe
from chat import process_new_matches
from adb import get_local_devices
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from appium.webdriver.appium_service import AppiumService
# Initialize rich console for better formatting
console = Console()

# Global variables
appium_process = None
connected_phone_id = None
driver = None

appium_service = None

def start_appium_server():
    """Starts the Appium server using the AppiumService class."""
    global appium_service
    
    # Define the host and port for clarity
    host = '127.0.0.1'
    port = '4723'
    server_url = f"http://{host}:{port}"
    
    # Check if a service object already exists and is running
    if appium_service and appium_service.is_running:
        console.print(f"[yellow]Appium server is already running at {server_url}[/yellow]")
        return server_url

    # Start the Appium server
    appium_service = AppiumService()
    try:
        console.print("[yellow]Starting Appium server...[/yellow]")
        appium_service.start(args=['--address', host, '--port', port])
        
        console.print(f"[green]Appium server started successfully at {server_url}[/green]")
        return server_url
        
    except Exception as e:
        # This handles the case where the port is already in use by another process
        if "main process already died" in str(e) or "Address already in use" in str(e):
             console.print(f"[yellow]Server appears to be already running. Attempting to connect to {server_url}[/yellow]")
             return server_url
        
        console.print(f"[red]Failed to start Appium server: {e}[/red]")
        raise RuntimeError("Could not start or connect to Appium server.")
def handle_update_popup(driver, timeout=0.5) -> bool:
    """
    Checks for the 'It's time to update' popup and clicks 'Maybe later' if present.

    Args:
        driver: Appium WebDriver instance.
        timeout (float): Max seconds to wait for popup appearance.

    Returns:
        bool: True if popup was handled, False otherwise.
    """
    try:
        # Quick check for the header text
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (AppiumBy.ID, "com.bumble.app:id/ctaBox_header")
            )
        )

        # Now find the 'Maybe later' button and click it
        maybe_later_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (AppiumBy.ID, "com.bumble.app:id/button_later")
            )
        )

        delay = random.uniform(0.2, 0.4)
        time.sleep(delay)
        maybe_later_btn.click()
        rprint(f"[green]Clicked 'Maybe later' on update popup.[/green]")
        return True

    except TimeoutException:
        return False
    except Exception as e:
        rprint(f"[red]Error handling update popup: {e}[/red]")
        return False

def get_device_info(connection_address: str) -> Tuple[str, str]:
    """
    Get device platform version and other info from ADB.
    
    Args:
        connection_address (str): The IP:port address of the connected device
        
    Returns:
        Tuple[str, str]: (platform_version, device_name)
    """
    try:
        # Get device properties
        cmd = ["adb", "-s", connection_address, "shell", "getprop"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extract platform version
        version_match = re.search(r'\[ro\.build\.version\.release\]:\s*\[(.*?)\]', result.stdout)
        platform_version = version_match.group(1) if version_match else "12"  # Default to 12 if not found
        
        return platform_version, connection_address
        
    except subprocess.CalledProcessError as e:
        rprint(f"[red]Failed to get device info: {e.stderr if isinstance(e.stderr, str) else e.stderr.decode()}[/red]")
        return "12", connection_address  # Default values if command fails
    except Exception as e:
        rprint(f"[red]Error getting device info: {str(e)}[/red]")
        return "12", connection_address  # Default values if command fails

def manage_adb_server(action: str = "kill") -> bool:
    """
    Manage the ADB server.
    
    Args:
        action (str): The action to perform ('kill' or 'start')
        
    Returns:
        bool: True if the action was successful, False otherwise
    """
    try:
        if action == "kill":
            rprint("[yellow]Killing ADB server...[/yellow]")
            subprocess.run(["adb", "kill-server"], check=True, capture_output=True)
            rprint("[green]ADB server killed successfully[/green]")
        elif action == "start":
            rprint("[yellow]Starting ADB server...[/yellow]")
            subprocess.run(["adb", "start-server"], check=True, capture_output=True)
            rprint("[green]ADB server started successfully[/green]")
        return True
    except subprocess.CalledProcessError as e:
        rprint(f"[red]Failed to {action} ADB server: {e.stderr.decode()}[/red]")
        return False
    except Exception as e:
        rprint(f"[red]Error managing ADB server: {str(e)}[/red]")
        return False

def setup_appium_driver(connection_info: dict,server_url:str) -> webdriver.Remote:
    """Set up and return an Appium WebDriver instance."""
    # Get device information
    connection_address = f"{connection_info['ip']}:{connection_info['port']}"
    platform_version, device_name = get_device_info(connection_address)
    
    rprint(f"[yellow]Appium server url: {server_url}[/yellow]")
    rprint(f"[yellow]Device platform version: {platform_version}[/yellow]")
    rprint(f"[yellow]Using device: {device_name}[/yellow]")
    
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.platform_version = platform_version
    options.device_name = device_name
    options.automation_name = "UiAutomator2"
    options.app_package = "com.bumble.app"
    options.app_activity = ".ui.launcher.BumbleLauncherActivity"  
    options.no_reset = True
    options.uiautomator2_server_install_timeout = 220000
    options.new_command_timeout = 300
    options.auto_grant_permissions = True
    options.adb_exec_timeout = 60000
    
    APPIUM_SERVER_URL = server_url
    
    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        retry = 0
        while retry < 3:
            time.sleep(1)  # Wait for app to load
            app_name = "com.bumble.app"
            if driver.current_package != app_name:
                driver.activate_app(app_name)
                retry += 1
                continue
            if handle_update_popup(driver):
                rprint("[blue]Update popup handled.[/blue]")
            return driver
        return None
    except Exception as e:
        rprint(f"[red]Failed to initialize Appium driver: {str(e)}[/red]")
        return None

def cleanup_phone():
    """Cleanup function to stop the connected phone and close the driver."""
    global connected_phone_id, driver, appium_service
    
    # Close the Appium driver if it exists
    if driver:
        try:
            rprint("[yellow]Closing Appium driver...[/yellow]")
            driver.quit()
        except Exception as e:
            rprint(f"[red]Error closing driver: {str(e)}[/red]")
        finally:
            driver = None
    
    # Stop the phone if it's connected
    if connected_phone_id:
        try:
            rprint("[yellow]Stopping phone...[/yellow]")
            stop_phone([connected_phone_id])
            rprint("[green]Phone stopped successfully[/green]")
        except Exception as e:
            rprint(f"[red]Error stopping phone: {str(e)}[/red]")
        finally:
            connected_phone_id = None
    
    # Kill ADB server after cleanup
    manage_adb_server("kill")

    if appium_service and appium_service.is_running:
        try:
            rprint("[yellow]Stopping Appium server...[/yellow]")
            appium_service.stop()
            rprint("[green]Appium server stopped successfully.[/green]")
        except Exception as e:
            rprint(f"[red]Error stopping Appium server: {e}[/red]")

def signal_handler(signum, frame):
    """Handle interruption signals."""
    rprint("\n[yellow]Interruption detected. Cleaning up...[/yellow]")
    cleanup_phone()

    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_phones(phones: List[Dict]):
    """Display phones in a formatted table."""
    table = Table(title="Available Phones")
    table.add_column("No.", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Brand", style="blue")
    table.add_column("Model", style="magenta")
    table.add_column("Type", style="cyan")

    for idx, phone in enumerate(phones, 1):
        status_color = "green" if phone["status"] == "active" else "red"
        device_type = phone.get("type", "remote")
        type_color = "blue" if device_type == "local" else "cyan"
        
        table.add_row(
            str(idx),
            phone["name"],
            f"[{status_color}]{phone['status']}[/{status_color}]",
            phone["brand"].title(),
            phone["model"],
            f"[{type_color}]{device_type}[/{type_color}]"
        )
    
    console.print(table)
    return phones

def get_automation_type():
    """Get the type of automation to perform."""
    console.print("\n[bold]Select Automation Type:[/bold]")
    console.print("1. Swiping")
    console.print("2. Handle Matches")
    console.print("3. Auto")
    
    choice = Prompt.ask("Select automation type", choices=["1", "2", "3"])
    automation_types = {
        "1": "swiping",
        "2": "handle_matches",
        "3": "auto"
    }
    return automation_types[choice]

def get_all_available_devices() -> List[Dict]:
    """Get all available devices (both remote and local)."""
    # Get remote devices
    remote_devices = get_available_phones()
    for device in remote_devices:
        device["type"] = "remote"
    
    # Get local devices
    local_devices = get_local_devices()
    
    # Combine both lists
    return remote_devices + local_devices

def start_automation_all(duration=None,probability=None):
    """Start automation for all phones."""
    devices = get_all_available_devices()
    if not devices:
        rprint("[red]No available devices found![/red]")
        return

    display_phones(devices)
    if Confirm.ask("Are you sure you want to start automation for all devices?"):
        automation_type = get_automation_type()

        if automation_type == "swiping":
            rprint("[yellow]Starting swipe automation...[/yellow]")
            # Get swipe duration from user
            if duration is None:
                duration = Prompt.ask(
                    "Enter swipe duration in minutes",
                    default="5",
                    show_default=True
                )
            try:
                duration = int(duration)
            except ValueError:
                duration = 5
                rprint("[yellow]Invalid duration. Using default of 5 minutes.[/yellow]")
            
            # Get right swipe probability
            if probability is None:
                probability = Prompt.ask(
                    "Enter right swipe probability (1-10)",
                    default="5",
                    show_default=True
                )
            try:
                probability = int(probability)
                if not 1 <= probability <= 10:
                    raise ValueError
            except ValueError:
                probability = 5
                rprint("[yellow]Invalid probability. Using default of 5.[/yellow]")

        # TODO: Implement actual automation start function
        rprint(f"[green]Starting {automation_type} automation for all devices...[/green]")
        for device in devices:
            device_name = device.get("name")
            rprint(f"[red]starting {device_name}[/red]")
            start_automation_specific(automation_type=automation_type,duration=duration,probability=probability,selected_device=device)

            rprint("[yellow]This is a placeholder for the actual implementation[/yellow]")

def start_automation_specific(automation_type=None,duration=None,probability=None,selected_device=None):
    """Start automation for a specific device."""
    global connected_phone_id, driver

    if selected_device is None:
        devices = get_all_available_devices()
        if not devices:
            rprint("[red]No available devices found![/red]")
            return

        devices = display_phones(devices)
        device_numbers = [str(i) for i in range(1, len(devices) + 1)]
        choice = Prompt.ask("Select device number", choices=device_numbers)
        
        selected_device = devices[int(choice) - 1]
    
    if automation_type is None:
        automation_type = get_automation_type()


    if automation_type == "swiping":
        rprint("[yellow]Starting swipe automation...[/yellow]")
        # Get swipe duration from user
        if duration is None:
            duration = Prompt.ask(
                "Enter swipe duration in minutes",
                default="5",
                show_default=True
            )
        try:
            duration = int(duration)
        except ValueError:
            duration = 5
            rprint("[yellow]Invalid duration. Using default of 5 minutes.[/yellow]")
        
        # Get right swipe probability
        if probability is None:
            probability = Prompt.ask(
                "Enter right swipe probability (1-10)",
                default="5",
                show_default=True
            )
        try:
            probability = int(probability)
            if not 1 <= probability <= 10:
                raise ValueError
        except ValueError:
            probability = 5
            rprint("[yellow]Invalid probability. Using default of 5.[/yellow]")
            
    # Kill ADB server before starting the process
    if not manage_adb_server("kill"):
        rprint("[red]Failed to kill ADB server. Cannot proceed.[/red]")
        return
    
    # Start ADB server
    if not manage_adb_server("start"):
        rprint("[red]Failed to start ADB server. Cannot proceed.[/red]")
        return
    
    # Handle device connection based on type
    if selected_device["type"] == "local":
        # For local devices, we can use them directly
        try:
            # Wait a moment for ADB server to fully start
            time.sleep(2)
            
            # Verify the device is still connected
            verify_cmd = ["adb", "devices"]
            result = subprocess.run(verify_cmd, capture_output=True, text=True, check=True)
            
            # Check if device is in the list of connected devices
            device_id = selected_device["id"]
            if device_id not in result.stdout:
                # Try to reconnect the device
                rprint(f"[yellow]Attempting to reconnect device {device_id}...[/yellow]")
                reconnect_cmd = ["adb", "connect", device_id]
                reconnect_result = subprocess.run(reconnect_cmd, capture_output=True, text=True, check=True)
                
                # Check again after reconnection attempt
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, check=True)
                if device_id not in verify_result.stdout:
                    rprint(f"[red]Device {device_id} is not connected and could not be reconnected![/red]")
                    return
                
            connection_info = {
                "ip": device_id.split(":")[0] if ":" in device_id else device_id,
                "port": device_id.split(":")[1] if ":" in device_id else "5555"
            }
            rprint(f"[green]Using local device: {selected_device['name']}[/green]")
        except subprocess.CalledProcessError as e:
            rprint(f"[red]Error verifying local device: {e.stderr if isinstance(e.stderr, str) else e.stderr.decode()}[/red]")
            return
    else:
        # For remote devices, use the existing connection process
        rprint(f"\n[yellow]Preparing {selected_device['name']} for automation...[/yellow]")
        connection_info = connect_to_phone(selected_device['id'])
        if not connection_info:
            rprint("[red]Failed to prepare device for automation. Please try again.[/red]")
            return
    
    # Store the connected device ID
    connected_phone_id = selected_device['id']
    
    
    try:
        # Set up Appium driver
        rprint("[yellow]Starting Appium server...[/yellow]")
        global appium_process
        server_url = start_appium_server()
        rprint("[yellow]Initializing Appium driver...[/yellow]")
        driver = setup_appium_driver(connection_info,server_url)
        if not driver:
            rprint("[red]Failed to initialize Appium driver. Stopping automation.[/red]")
            return
            
        rprint("[green]Appium driver initialized successfully[/green]")
        
        # Execute the selected automation type
            # Start the swipe automation

        if automation_type == "swiping":
            if open_page(driver, "People"): 
                realistic_swipe(driver, right_swipe_probability=probability, duration_minutes=duration)
        elif automation_type == "handle_matches":
            if open_page(driver, "Chats"): 
                process_new_matches(driver,10,5)
                print("Finished chat processing phase.")
        elif automation_type == "auto":
            for i in range(2):
                if open_page(driver, "People"): 
                    realistic_swipe(driver, right_swipe_probability=7, duration_minutes=5)

                if open_page(driver, "Chats"): 
                    process_new_matches(driver,10,5)
                    print("Finished chat processing phase.")
            
    except Exception as e:
        rprint(f"[red]An error occurred during automation: {str(e)}[/red]")
        rprint("[yellow]Detailed error information:[/yellow]")
        import traceback
        rprint(traceback.format_exc())
    finally:
        cleanup_phone()

def list_available_phones():
    """List all available devices."""
    devices = get_all_available_devices()
    if not devices:
        rprint("[red]No available devices found![/red]")
        return
    
    display_phones(devices)

def disable_phone():
    """Disable a phone from automation."""
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return

    phones = display_phones(phones)
    phone_numbers = [str(i) for i in range(1, len(phones) + 1)]
    choice = Prompt.ask("Select phone number to disable", choices=phone_numbers)
    
    selected_phone = phones[int(choice) - 1]
    
    if Confirm.ask(f"Are you sure you want to disable {selected_phone['name']}?"):
        # TODO: Implement actual phone disable function
        rprint(f"[red]Disabling {selected_phone['name']}...[/red]")
        rprint("[yellow]This is a placeholder for the actual implementation[/yellow]")

def show_menu():
    """Display the main menu."""
    while True:
        clear_screen()
        console.print("[bold blue]Phone Automation Dashboard[/bold blue]")
        console.print("\n[bold]Available Options:[/bold]")
        console.print("1. Start Automation for All Devices")
        console.print("2. Start Automation for Specific Device")
        console.print("3. List Available Devices")
        console.print("4. Disable Device")
        console.print("5. Exit")
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5"])
        
        if choice == "1":
            start_automation_all()
        elif choice == "2":
            start_automation_specific()
        elif choice == "3":
            list_available_phones()
        elif choice == "4":
            disable_phone()
        elif choice == "5":
            if Confirm.ask("Are you sure you want to exit?"):
                cleanup_phone()
                console.print("[yellow]Goodbye![/yellow]")
                break
        
        Prompt.ask("\nPress Enter to continue")

if __name__ == "__main__":
    try:
        show_menu()
    except KeyboardInterrupt:
        cleanup_phone()
        console.print("\n[yellow]Program terminated by user[/yellow]")
    except Exception as e:
        cleanup_phone()
        console.print(f"[red]An error occurred: {str(e)}[/red]")
