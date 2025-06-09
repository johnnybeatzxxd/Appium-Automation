import os
import signal
import sys
import time
import subprocess
import re
from typing import List, Dict, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from geelark_api import get_available_phones, stop_phone
from connection import connect_to_phone
from appium import webdriver
from appium.options.android import UiAutomator2Options
from swipe import realistic_swipe

# Initialize rich console for better formatting
console = Console()

# Global variables
connected_phone_id = None
driver = None

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
        rprint(f"[red]Failed to get device info: {e.stderr.decode()}[/red]")
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

def setup_appium_driver(connection_info: dict) -> webdriver.Remote:
    """Set up and return an Appium WebDriver instance."""
    # Get device information
    connection_address = f"{connection_info['ip']}:{connection_info['port']}"
    platform_version, device_name = get_device_info(connection_address)
    
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
    
    APPIUM_SERVER_URL = "http://127.0.0.1:4723"
    
    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        time.sleep(5)  # Wait for app to load
        return driver
    except Exception as e:
        rprint(f"[red]Failed to initialize Appium driver: {str(e)}[/red]")
        return None

def cleanup_phone():
    """Cleanup function to stop the connected phone and close the driver."""
    global connected_phone_id, driver
    
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

    for idx, phone in enumerate(phones, 1):
        status_color = "green" if phone["status"] == "active" else "red"
        table.add_row(
            str(idx),
            phone["name"],
            f"[{status_color}]{phone['status']}[/{status_color}]",
            phone["brand"].title(),
            phone["model"]
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

def start_automation_all():
    """Start automation for all phones."""
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return

    display_phones(phones)
    if Confirm.ask("Are you sure you want to start automation for all phones?"):
        automation_type = get_automation_type()
        # TODO: Implement actual automation start function
        rprint(f"[green]Starting {automation_type} automation for all phones...[/green]")
        rprint("[yellow]This is a placeholder for the actual implementation[/yellow]")

def start_automation_specific():
    """Start automation for a specific phone."""
    global connected_phone_id, driver
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return

    phones = display_phones(phones)
    phone_numbers = [str(i) for i in range(1, len(phones) + 1)]
    choice = Prompt.ask("Select phone number", choices=phone_numbers)
    
    selected_phone = phones[int(choice) - 1]
    
    # Kill ADB server before starting the process
    if not manage_adb_server("kill"):
        rprint("[red]Failed to kill ADB server. Cannot proceed.[/red]")
        return
    
    # Start ADB server
    if not manage_adb_server("start"):
        rprint("[red]Failed to start ADB server. Cannot proceed.[/red]")
        return
    
    # First make sure the phone is connected and ready
    rprint(f"\n[yellow]Preparing {selected_phone['name']} for automation...[/yellow]")
    connection_info = connect_to_phone(selected_phone['id'])
    if not connection_info:
        rprint("[red]Failed to prepare phone for automation. Please try again.[/red]")
        return
    
    # Store the connected phone ID
    connected_phone_id = selected_phone['id']
    
    # Get automation type
    automation_type = get_automation_type()
    
    try:
        # Set up Appium driver
        rprint("[yellow]Initializing Appium driver...[/yellow]")
        driver = setup_appium_driver(connection_info)
        if not driver:
            rprint("[red]Failed to initialize Appium driver. Stopping automation.[/red]")
            return
            
        rprint("[green]Appium driver initialized successfully[/green]")
        
        # Execute the selected automation type
        if automation_type == "swiping":
            rprint("[yellow]Starting swipe automation...[/yellow]")
            # Get swipe duration from user
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
            
            # Start the swipe automation
            realistic_swipe(driver, right_swipe_probability=probability, duration_minutes=duration)
            
        elif automation_type == "handle_matches":
            rprint("[yellow]Handle matches automation not implemented yet[/yellow]")
        elif automation_type == "auto":
            rprint("[yellow]Auto automation not implemented yet[/yellow]")
            
    except Exception as e:
        rprint(f"[red]An error occurred during automation: {str(e)}[/red]")
    finally:
        cleanup_phone()

def list_available_phones():
    """List all available phones."""
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return
    
    display_phones(phones)

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
        console.print("1. Start Automation for All Phones")
        console.print("2. Start Automation for Specific Phone")
        console.print("3. List Available Phones")
        console.print("4. Disable Phone")
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
