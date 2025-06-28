import os
import signal
import sys
import time
import subprocess
import re
import threading
import multiprocessing
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from rich.text import Text
from typing import Callable 
from geelark_api import get_available_phones, stop_phone, start_phone
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

def open_phones_manually():
    """
    Starts a persistent, interactive session for manually using cloud phones,
    ensuring all phones are stopped on exit.
    """
    console.print("\n[bold green]Manual Phone Session Manager[/bold green]")
    
    remote_phones = get_available_phones(adb_enabled=False)
    if not remote_phones:
        rprint("[red]No remote phones available.[/red]")
        return

    display_phones(remote_phones)
    
    # <<< FIX 1: The prompt text is now shorter and mentions 'all' >>>
    selection_str = Prompt.ask(
        "Enter numbers separated by space to open (e.g. 1 3 4), 'all', or press Enter to cancel"
    )

    if not selection_str.strip():
        rprint("[yellow]Operation cancelled.[/yellow]")
        return

    # --- Initial Selection Processing ---
    ids_to_start = []
    selected_phone_map = {} 

    # <<< FIX 2: Added logic to handle the 'all' keyword >>>
    if selection_str.strip().lower() == 'all':
        rprint("[cyan]Selecting all available phones...[/cyan]")
        ids_to_start = [phone['id'] for phone in remote_phones]
        # Map all phones by their original index number (as a string)
        selected_phone_map = {str(i + 1): phone for i, phone in enumerate(remote_phones)}
    else:
        # This is the original logic for processing individual numbers
        user_choices = selection_str.strip().split()
        for choice in user_choices:
            if not choice.isdigit() or not (1 <= int(choice) <= len(remote_phones)):
                rprint(f"[yellow]Warning: Invalid choice '{choice}'. Skipping.[/yellow]")
                continue
            
            choice_idx = int(choice) - 1
            phone_data = remote_phones[choice_idx]
            ids_to_start.append(phone_data['id'])
            selected_phone_map[choice] = phone_data

    if not ids_to_start:
        rprint("[red]No valid phones were selected. Aborting.[/red]")
        return
    # --- Session Management with Guaranteed Cleanup ---
    # This list will hold the IDs of phones that were successfully started
    active_phone_ids = []
    try:
        rprint(f"\n[cyan]Attempting to start {len(ids_to_start)} phone(s)...[/cyan]")
        response = start_phone(ids_to_start)
        
        # Check the API response to see which phones ACTUALLY started
        if response and response.get("code") == 0:
            success_details = response.get("data", {}).get("successDetails", [])
            active_phone_ids = [phone['id'] for phone in success_details]
            if not active_phone_ids:
                 rprint("[red]API call succeeded, but no phones were actually started. Check phone status on the platform.[/red]")
                 return
            rprint("[bold green]Success! The following phone screens should have opened:[/bold green]")
        else:
            rprint("[bold red]Failed to start phones. Please check the API response above.[/bold red]")
            return

        # This is the interactive shutdown loop
        while active_phone_ids:
            # Display the currently active phones
            active_phones_table = Table(title="Currently Active Phones")
            active_phones_table.add_column("No.", style="cyan")
            active_phones_table.add_column("Name", style="green")
            active_phones_table.add_column("ID", style="yellow")
            
            # Find the original menu number for each active phone
            for original_number, phone_data in selected_phone_map.items():
                if phone_data['id'] in active_phone_ids:
                    active_phones_table.add_row(original_number, phone_data['name'], phone_data['id'])
            
            console.print(active_phones_table)

            shutdown_choice_str = Prompt.ask(
                "\nEnter numbers to shut down, type [bold]'all'[/bold] to stop everything, or press [bold]Ctrl+C[/bold] to exit"
            )

            ids_to_stop = []
            if shutdown_choice_str.strip().lower() == 'all':
                ids_to_stop = list(active_phone_ids) # Make a copy
            else:
                for choice in shutdown_choice_str.strip().split():
                    # Check if the chosen number corresponds to a currently active phone
                    if choice in selected_phone_map and selected_phone_map[choice]['id'] in active_phone_ids:
                        ids_to_stop.append(selected_phone_map[choice]['id'])
                    else:
                        rprint(f"[yellow]Warning: '{choice}' is not a valid active phone number. Skipping.[/yellow]")

            if ids_to_stop:
                rprint(f"\n[cyan]Sending stop command for {len(ids_to_stop)} phone(s)...[/cyan]")
                stop_phone(ids_to_stop)
                # Remove the stopped phones from our active list
                active_phone_ids = [pid for pid in active_phone_ids if pid not in ids_to_stop]

        rprint("\n[bold green]All manually opened phones have been shut down.[/bold green]")

    finally:
        # This block is GUARANTEED to run on any exit, including Ctrl+C
        if active_phone_ids:
            rprint("\n[bold yellow]Exiting session. Ensuring all remaining active phones are stopped...[/bold yellow]")
            try:
                stop_phone(active_phone_ids)
                rprint("[green]Cleanup complete. All phones stopped.[/green]")
            except Exception as e:
                rprint(f"[bold red]CRITICAL: Cleanup failed. Could not stop phones {active_phone_ids}. Please check your provider's dashboard manually! Error: {e}[/bold red]")

def create_device_logger(device_name: str):
    """
    Creates and returns a logging function that automatically prepends the device name
    and correctly preserves color markup.
    """
    # Create the prefix as a rich-formatted string
    prefix_str = f"[bold cyan][{device_name}][/bold cyan]"

    def device_specific_log(message: str, *args, **kwargs):
        """The actual logging function that will be used in the process."""
        # Combine the prefix string and the message string *before* printing
        full_message_str = f"{prefix_str} {message}"
        
        # rprint will now parse the ENTIRE string for all markup tags
        rprint(full_message_str, *args, **kwargs)

    return device_specific_log

def run_automation_for_device(device: Dict, automation_type: str, appium_port: int, system_port: int, duration: int, probability: int):
    """
    This function contains all logic to automate a SINGLE phone.
    It's designed to be run in its own process.
    """
    device_name = device.get('name', 'UnknownDevice')
    
    # === NEW: Create the logger for this specific device ===
    log = create_device_logger(device_name)
    
    appium_service = None
    driver = None

    try:
        log("Automation process started.")
        
        # 1. Connect to the physical device
        if device["type"] == "local":
            connection_info = { "ip": device["id"].split(":")[0], "port": device["id"].split(":")[1] }
        else: # remote
            connection_info = connect_to_phone(device['id'])

        if not connection_info:
            log("[red]Failed to get connection info. Terminating.[/red]")
            return

        # 2. Start a unique Appium Service for this device
        # Pass the logger to any functions that need it
        appium_service = start_appium_service_instance('127.0.0.1', appium_port, system_port, log)
        server_url = f"http://127.0.0.1:{appium_port}/wd/hub"

        # 3. Setup the Appium Driver
        driver = setup_appium_driver(connection_info, server_url, system_port)
        if not driver:
            log("[red]Failed to initialize driver. Terminating.[/red]")
            return

        log("[green]Setup complete. Starting automation logic.[/green]")

        # 4. Execute the automation logic, passing the logger
        if automation_type == "swiping":
            # Pass the log function to your helper functions
            if open_page(driver, "People", logger_func=log): 
                realistic_swipe(driver, right_swipe_probability=probability, duration_minutes=duration, logger_func=log)
        elif automation_type == "handle_matches":
            if open_page(driver, "Chats", logger_func=log): 
                process_new_matches(driver, 10, 5, logger_func=log)
        elif automation_type == "auto":
             for i in range(2):
                if open_page(driver, "People", logger_func=log): 
                    realistic_swipe(driver, right_swipe_probability=7, duration_minutes=5, logger_func=log)
                if open_page(driver, "Chats", logger_func=log): 
                    process_new_matches(driver,10, 5, logger_func=log)

        log("[green]Automation task finished.[/green]")
    except Exception as e:
        log(f"[red]An unexpected error occurred: {e}[/red]")
        import traceback
        log(traceback.format_exc())
    finally:
        # 5. Cleanup (this is critical!)
        log("Starting cleanup...")
        if driver:
            try:
                driver.quit()
                log("Appium driver quit successfully.")
            except Exception as e:
                log(f"[red]Error quitting driver: {e}[/red]")
        if appium_service:
            try:
                appium_service.stop()
                log("Appium service stopped successfully.")
            except Exception as e:
                log(f"[red]Error stopping Appium service: {e}[/red]")
        if device["type"] != "local":
            stop_phone([device['id']])
            log("Remote phone stop signal sent.")
        log("Cleanup finished.")
def start_appium_service_instance(host: str, port: int, system_port: int, log: Callable) -> AppiumService:
    """Starts a unique Appium server instance on a specific port."""
    service = AppiumService()
    log(f"[yellow]Attempting to start Appium on {host}:{port} for system port {system_port}...[/yellow]")
    try:
        service.start(
            args=[
                '--address', host,
                '--port', str(port),
                '--session-override',
                '--log-timestamp',
                '--log-no-colors',
                # This is crucial for parallel Android execution
                '--base-path', f'/wd/hub',
                '--default-capabilities', f'{{"systemPort": {system_port}}}'
            ],
            timeout_ms=30000
        )
        log(f"[green]Appium server started for device on port {port}[/green]")
        return service
    except Exception as e:
        log(f"[red]Failed to start Appium server on port {port}: {e}[/red]")
        # Check if error message indicates it's already running
        if "main process already died" in str(e) or "Address already in use" in str(e):
             log(f"[yellow]Server on port {port} may already be running. Will attempt to connect.[/yellow]")
             return None # Indicate that we should just try to connect
        raise RuntimeError(f"Could not start Appium server on port {port}.")

def handle_update_popup(driver, timeout=3) -> bool:
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
        log(f"[green]Clicked 'Maybe later' on update popup.[/green]")
        return True

    except TimeoutException:
        return False
    except Exception as e:
        log(f"[red]Error handling update popup: {e}[/red]")
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
    """Manage the ADB server."""
    try:
        if action == "kill":
            rprint("[yellow]Killing ADB server...[/yellow]")
            subprocess.run(["adb", "kill-server"], check=True, capture_output=True, text=True)
            rprint("[green]ADB server killed successfully[/green]")
        elif action == "start":
            rprint("[yellow]Starting ADB server...[/yellow]")
            subprocess.run(["adb", "start-server"], check=True, capture_output=True, text=True)
            rprint("[green]ADB server started successfully[/green]")
        return True
    except subprocess.CalledProcessError as e:
        rprint(f"[red]Failed to {action} ADB server: {e.stderr}[/red]")
        return False
    except Exception as e:
        rprint(f"[red]Error managing ADB server: {str(e)}[/red]")
        return False

def setup_appium_driver(connection_info: dict, server_url: str, system_port: int) -> webdriver.Remote:
    """Set up and return an Appium WebDriver instance for a specific device."""
    connection_address = f"{connection_info['ip']}:{connection_info['port']}"
    platform_version, device_name = "12", connection_address # Simplified for example

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = device_name
    options.udid = device_name # Explicitly set UDID
    options.automation_name = "UiAutomator2"
    options.app_package = "com.bumble.app"
    options.app_activity = ".ui.launcher.BumbleLauncherActivity"
    options.no_reset = True
    options.new_command_timeout = 300
    options.auto_grant_permissions = True
    # CRUCIAL for parallel execution: each device needs a unique systemPort
    options.system_port = system_port

    try:
        rprint(f"[{device_name}] Connecting to Appium at {server_url}...")
        driver = webdriver.Remote(server_url, options=options)
        time.sleep(5) # Wait for app to stabilize
        rprint(f"[{device_name}] Driver initialized successfully.")
        return driver
    except Exception as e:
        rprint(f"[{device_name}] [red]Failed to initialize Appium driver: {str(e)}[/red]")
        return None

def signal_handler(signum, frame):
    """
    Handle interruption signals gracefully.
    The 'finally' blocks in the running functions are responsible for the actual cleanup.
    """
    rprint("\n\n[bold yellow]Interruption detected! Asking the running process to exit gracefully...[/bold yellow]")
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

def start_automation_all():
    """Manages the parallel execution of automation across selected devices."""
    # 1. Get all available devices
    devices = get_all_available_devices()
    if not devices:
        rprint("[red]No available devices found![/red]")
        return

    display_phones(devices)
    
    # 2. Prompt for device selection
    selection_str = Prompt.ask(
        "Enter numbers separated by space to select devices (e.g. 1 3 4), 'all', or press Enter to cancel"
    )

    if not selection_str.strip():
        rprint("[yellow]Operation cancelled.[/yellow]")
        return

    # 3. Process selection
    selected_devices = []
    if selection_str.strip().lower() == 'all':
        rprint("[cyan]Selecting all available devices...[/cyan]")
        selected_devices = devices
    else:
        user_choices = selection_str.strip().split()
        for choice in user_choices:
            if not choice.isdigit() or not (1 <= int(choice) <= len(devices)):
                rprint(f"[yellow]Warning: Invalid choice '{choice}'. Skipping.[/yellow]")
                continue
            selected_devices.append(devices[int(choice) - 1])

    if not selected_devices:
        rprint("[red]No valid devices were selected. Aborting.[/red]")
        return

    # 4. Get automation parameters
    automation_type = get_automation_type()
    duration = 5
    probability = 5

    if automation_type == "swiping":
        duration_str = Prompt.ask("Enter swipe duration in minutes", default="5")
        duration = int(duration_str) if duration_str.isdigit() else 5
        
        prob_str = Prompt.ask("Enter right swipe probability (1-10)", default="5")
        probability = int(prob_str) if prob_str.isdigit() and 1 <= int(prob_str) <= 10 else 5

    # 5. Prepare for multiprocessing
    manage_adb_server("kill") # Kill any old server
    manage_adb_server("start") # Start one clean server for all processes

    processes = []
    try:
        appium_base_port = 4723
        system_base_port = 8200 # Each UiAutomator2 instance needs a unique system port

        # 6. Create and start a process for each selected device
        rprint("\n[bold blue]Starting automation processes...[/bold blue]")
        for i, device in enumerate(selected_devices):
            appium_port = appium_base_port + (i * 2) # e.g., 4723, 4725, 4727
            system_port = system_base_port + i       # e.g., 8200, 8201, 8202

            process = multiprocessing.Process(
                target=run_automation_for_device,
                args=(device, automation_type, appium_port, system_port, duration, probability)
            )
            processes.append(process)
            process.start()
            rprint(f"[green]Started process {process.pid} for device '{device['name']}' on Appium port {appium_port}[/green]")
            time.sleep(5) # Stagger the process starts slightly to avoid resource contention

        # 7. Wait for all processes to complete
        rprint("\n[bold yellow]All automation processes are running. Waiting for them to complete...[/bold yellow]")
        for process in processes:
            process.join() # This will block until the process finishes

        rprint("\n[bold green]All automation tasks have completed.[/bold green]")
        manage_adb_server("kill") # Final cleanup
    finally:
        # This block is GUARANTEED to run, even on Ctrl+C
        rprint("\n[bold yellow]Main process is shutting down...[/bold yellow]")

        # 1. Find all remote phones that were part of this run.
        remote_device_ids = [
            device['id'] for device in selected_devices if device.get("type") == "remote"
        ]

        # 2. If there are any, call the stop_phone API for all of them.
        if remote_device_ids:
            rprint(f"[yellow]Sending stop command for {len(remote_device_ids)} remote phone(s)...[/yellow]")
            try:
                # The stop_phone function likely accepts a list of IDs.
                stop_phone(remote_device_ids)
                rprint("[green]Stop command sent successfully.[/green]")
            except Exception as e:
                rprint(f"[bold red]CRITICAL: Failed to send stop command for phones: {e}[/bold red]")
        
        # 3. Now, proceed with terminating the local child processes.
        rprint("[yellow]Terminating all child processes...[/yellow]")
        for process in processes:
            if process.is_alive():
                rprint(f"[red]Terminating process {process.pid}...[/red]")
                process.terminate()
                process.join(timeout=5)
        
        rprint("[green]All child processes have been terminated.[/green]")
        manage_adb_server("kill")

def start_automation_specific():
    """Start automation for a single, user-selected device."""
    # Define local variables for cleanup.
    driver = None
    appium_service = None
    selected_device = None

    try:
        # --- GATHER USER INPUT ---
        devices = get_all_available_devices()
        if not devices:
            rprint("[red]No available devices found![/red]")
            return

        display_phones(devices)
        device_numbers = [str(i) for i in range(1, len(devices) + 1)]
        choice = Prompt.ask("Select device number", choices=device_numbers)
        selected_device = devices[int(choice) - 1]
    
        automation_type = get_automation_type()
        duration = 5
        probability = 5

        if automation_type == "swiping":
            duration_str = Prompt.ask("Enter swipe duration in minutes", default="5")
            duration = int(duration_str) if duration_str.isdigit() else 5
            prob_str = Prompt.ask("Enter right swipe probability (1-10)", default="5")
            probability = int(prob_str) if prob_str.isdigit() and 1 <= int(prob_str) <= 10 else 5
        
        # --- SETUP LOGGING AND ENVIRONMENT ---
        device_name = selected_device.get('name', 'UnknownDevice')
        log = create_device_logger(device_name)
        
        # <<< FIX 1: REMOVED THE CALLS to initialize_swipe_logger and initialize_chat_logger >>>
        # They are not needed.

        manage_adb_server("kill")
        manage_adb_server("start")
        
        # --- CONNECT AND INITIALIZE ---
        if selected_device["type"] == "local":
            connection_info = { "ip": selected_device["id"].split(":")[0], "port": selected_device["id"].split(":")[1] }
            log(f"[green]Using local device: {selected_device['name']}[/green]")
        else:
            log(f"\n[yellow]Preparing {selected_device['name']} for automation...[/yellow]")
            connection_info = connect_to_phone(selected_device['id'])
        
        if not connection_info:
            log("[red]Failed to prepare device for automation. Please try again.[/red]")
            return
        
        appium_port = 4723
        system_port = 8200
        server_url = f"http://127.0.0.1:{appium_port}/wd/hub"

        log("[yellow]Starting Appium server...[/yellow]")
        appium_service = start_appium_service_instance('127.0.0.1', appium_port, system_port, log)
        
        log("[yellow]Initializing Appium driver...[/yellow]")
        driver = setup_appium_driver(connection_info, server_url, system_port)
        if not driver:
            log("[red]Failed to initialize Appium driver. Stopping automation.[/red]")
            return
            
        log("[green]Appium driver initialized successfully[/green]")
        
        if automation_type == "swiping":
            if open_page(driver, "People",logger_func=log): 
                realistic_swipe(driver, right_swipe_probability=probability, duration_minutes=duration, logger_func=log)
        elif automation_type == "handle_matches":
            if open_page(driver, "Chats",logger_func=log): 
                process_new_matches(driver, 10, 5,logger_func=log)
        elif automation_type == "auto":
            for i in range(2):
                if open_page(driver, "People", logger_func=log): 
                    realistic_swipe(driver, right_swipe_probability=7, duration_minutes=5, logger_func=log)
                if open_page(driver, "Chats",logger_func=log): 
                    process_new_matches(driver,10, 5, logger_func=log)
            
    except Exception as e:
        # Use rprint here to be safe in case the 'log' function itself has an issue.
        rprint(f"[bold red]An error occurred during automation: {str(e)}[/bold red]")
        import traceback
        rprint(traceback.format_exc())
    finally:
        # This local cleanup is correct. Do not change it.
        rprint("\n[bold yellow]Cleaning up resources...[/bold yellow]")
        if driver:
            try:
                driver.quit()
                rprint("[green]Appium driver closed.[/green]")
            except Exception as e:
                if "A session is either terminated or not started" in str(e):
                    rprint("[yellow]Could not quit driver (session was already closed, this is normal on exit).[/yellow]")
                else:
                    # If it's a different error, print it in red because it was unexpected.
                    rprint(f"[red]An unexpected error occurred while closing the driver: {str(e)}[/red]")
        
        if appium_service and appium_service.is_running:
            try:
                appium_service.stop()
                rprint("[green]Appium server stopped.[/green]")
            except Exception as e:
                rprint(f"[red]Error stopping Appium server: {e}[/red]")
        
        if selected_device and selected_device["type"] == "remote":
            try:
                stop_phone([selected_device['id']])
                rprint(f"[green]Phone stop signal sent for {selected_device['name']}.[/green]")
            except Exception as e:
                rprint(f"[red]Error stopping phone: {str(e)}[/red]")
        
        manage_adb_server("kill")
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
        console.print("1. Start Automation for Multiple Devices")
        console.print("2. Start Automation for Specific Device")
        console.print("3. List Available Devices")
        console.print("4. Disable Device")
        console.print("5. Open Phones for Manual Use")  
        console.print("6. Exit")                      
        
        choice = Prompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5", "6"])
        
        if choice == "1":
            start_automation_all()
        elif choice == "2":
            start_automation_specific()
        elif choice == "3":
            list_available_phones()
        elif choice == "4":
            disable_phone()
        elif choice == "5":
            # Call the new function
            open_phones_manually()
        elif choice == "6":
            # The clean exit logic
            if Confirm.ask("Are you sure you want to exit?"):
                console.print("[yellow]Goodbye![/yellow]")
                break
        
        Prompt.ask("\nPress Enter to continue")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        show_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]Program terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
