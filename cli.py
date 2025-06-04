import os
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from geelark_api import get_available_phones

# Initialize rich console for better formatting
console = Console()

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

def start_automation_all():
    """Start automation for all phones."""
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return

    display_phones(phones)
    if Confirm.ask("Are you sure you want to start automation for all phones?"):
        # TODO: Implement actual automation start function
        rprint("[green]Starting automation for all phones...[/green]")
        rprint("[yellow]This is a placeholder for the actual implementation[/yellow]")

def start_automation_specific():
    """Start automation for a specific phone."""
    phones = get_available_phones()
    if not phones:
        rprint("[red]No available phones found![/red]")
        return

    phones = display_phones(phones)
    phone_numbers = [str(i) for i in range(1, len(phones) + 1)]
    choice = Prompt.ask("Select phone number", choices=phone_numbers)
    
    selected_phone = phones[int(choice) - 1]
    
    # TODO: Implement actual automation start function for specific phone
    rprint(f"[green]Starting automation for {selected_phone['name']}...[/green]")
    rprint("[yellow]This is a placeholder for the actual implementation[/yellow]")

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
                console.print("[yellow]Goodbye![/yellow]")
                break
        
        Prompt.ask("\nPress Enter to continue")

if __name__ == "__main__":
    try:
        show_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]Program terminated by user[/yellow]")
    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
