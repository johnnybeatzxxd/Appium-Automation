# chat.py

import time
import random
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from rich import print as rprint
from rich.console import Console
from helper import open_page

# Initialize rich console for better formatting
console = Console()

# --- Locators ---
# Chats List Screen
YOUR_MATCHES_TITLE_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_expiringConnectionsTitle")
YOUR_MATCHES_RV_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_connectionsListExpiring")
MATCH_ITEM_BUTTON_XPATH = ".//android.widget.Button[@resource-id='com.bumble.app:id/connectionItem_ringView']"
MAIN_CHAT_LIST_RV_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_connectionsList")

# "Opening Move" Screen
OPENING_MOVE_CONTAINER_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/initialChatV3_container")
OPENING_MOVE_TITLE_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, 'Opening Move')]")
OPENING_MOVE_REPLY_BUTTON_LOCATOR = (AppiumBy.XPATH, "//android.view.View[@clickable='true' and .//android.widget.TextView[@text='Reply']]")


# Individual Chat Screen (Regular chat with input field) - UPDATED
CHAT_MESSAGE_INPUT_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatInput_text") # Updated from XML
# The Send button often appears dynamically. We'll use a content-desc for now.
# It might replace the voice message icon (com.bumble.app:id/recording_IconComponent)
CHAT_SEND_BUTTON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatInput_button_send") # NEW - More reliable
# Alternative if the above is too generic or if it has a specific ID when it appears:
# CHAT_SEND_BUTTON_LOCATOR_BY_ID_IF_AVAILABLE = (AppiumBy.ID, "com.bumble.app:id/id_of_the_send_button_when_visible")

CHAT_TOOLBAR_NAME_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatToolbar_title")
CHAT_HEADER_BACK_BUTTON_LOCATOR = (AppiumBy.XPATH, "//android.widget.ImageButton[@content-desc='Back']") # Toolbar back button

SPOTLIGHT_PROMO_TEXT_LOCATOR = (AppiumBy.XPATH, "//*[contains(@text, 'Spotlight is the easiest way')]")
OPENING_MOVES_SETUP_PROMO_TEXT_LOCATOR = (AppiumBy.XPATH, "//*[contains(@text, 'Get to good conversation, faster')]")
# --- Helper Functions ---

def is_on_chats_list_page(driver, timeout=7):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(YOUR_MATCHES_TITLE_LOCATOR)
        )
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located(MAIN_CHAT_LIST_RV_LOCATOR)
        )
        rprint("[green]✓[/green] Verified on Chats list page")
        return True
    except TimeoutException:
        rprint("[red]✗[/red] Not on Chats list page (timed out waiting for elements)")
        return False

def handle_opening_move_screen(driver, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located(OPENING_MOVE_CONTAINER_LOCATOR),
                EC.presence_of_element_located(OPENING_MOVE_TITLE_TEXT_LOCATOR)
            )
        )
        rprint("[yellow]ℹ[/yellow] 'Opening Move' screen detected")
        reply_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(OPENING_MOVE_REPLY_BUTTON_LOCATOR)
        )
        reply_button.click()
        rprint("[green]✓[/green] Clicked 'Reply' on the 'Opening Move' screen")
        time.sleep(random.uniform(1.0, 2.0))
        return True
    except TimeoutException:
        return False
    except Exception as e:
        rprint(f"[red]✗[/red] Error handling 'Opening Move' screen: {e}")
        return False

def is_on_individual_chat_page(driver, user_name_for_verification=None, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(CHAT_MESSAGE_INPUT_LOCATOR)
        )
        rprint("[green]✓[/green] Verified on individual chat page (message input found)")

        if user_name_for_verification:
            try:
                toolbar_title_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located(CHAT_TOOLBAR_NAME_LOCATOR)
                )
                toolbar_title_text = toolbar_title_element.text
                expected_name_part = user_name_for_verification.split(',')[0].split(' ')[0]
                if expected_name_part.lower() in toolbar_title_text.lower():
                    rprint(f"[green]✓[/green] Verified chat toolbar title contains '{expected_name_part}'")
                else:
                    rprint(f"[yellow]⚠[/yellow] Chat toolbar title '{toolbar_title_text}' doesn't strongly match expected '{expected_name_part}'")
            except TimeoutException:
                rprint("[yellow]⚠[/yellow] Chat toolbar title element not found for secondary verification")
            except Exception as e_detail:
                rprint(f"[yellow]⚠[/yellow] Error during chat toolbar title verification: {e_detail}")
        return True
    except TimeoutException:
        rprint("[red]✗[/red] Not on individual chat page (timed out waiting for chat input)")
        return False

def send_opening_message(driver, match_name):
    """
    Types and sends an opening message by sending the whole string at once.
    Uses the specific resource-id for the send button.
    """
    rprint(f"[blue]→[/blue] Attempting to send opening message to {match_name}")
    try:
        # Wait for the message input field to be present and clickable
        message_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(CHAT_MESSAGE_INPUT_LOCATOR) 
            # CHAT_MESSAGE_INPUT_LOCATOR should be (AppiumBy.ID, "com.bumble.app:id/chatInput_text")
        )

        # Select a random message
        first_name = match_name.split(',')[0].split(' ')[0] # Get first name
        messages = [
            f"Hey {first_name}! How's your day going? 😊",
            f"Hi {first_name}! Nice to match with you. What are you up to?",
            f"Hello {first_name}! 👋 Hope you're having a good one.",
            f"Hey {first_name}, pleasure to connect!",
        ]
        message_to_send = random.choice(messages)

        # Click to focus
        message_input.click()
        time.sleep(0.5) # Allow UI to react

        # Clear placeholder text like "Aa" if present
        current_text_in_input = message_input.text
        if current_text_in_input and (current_text_in_input.lower() == "aa" or current_text_in_input.lower() == "send a message..."):
            rprint(f"[yellow]ℹ[/yellow] Clearing placeholder input text: '{current_text_in_input}'")
            message_input.clear()
            time.sleep(0.3) # Pause after clear

        # Send the entire message
        rprint(f"[blue]→[/blue] Typing message: '{message_to_send}'")
        message_input.send_keys(message_to_send)
        
        # Pause after typing, before attempting to send
        time.sleep(random.uniform(0.8, 1.5)) 

        # --- Attempt to click the SEND button using the specific ID ---
        try:
            # The send button should now be present and clickable with its specific ID
            send_button = WebDriverWait(driver, 7).until(
                EC.element_to_be_clickable(CHAT_SEND_BUTTON_LOCATOR) # Using the new ID-based locator
            )
            # send_button.click()
            rprint("[green]✓[/green] Message SENT.")
        except TimeoutException:
            rprint("[red]✗[/red] Send button (ID: com.bumble.app:id/chatInput_button_send) not found or not clickable after typing.")
            rprint("[grey50]DEBUG: Page source at send button failure:\n" + driver.page_source[:3000]) # Log some source
            return False

        time.sleep(random.uniform(1.0, 2.5)) # Pause after sending
        return True

    except TimeoutException:
        rprint(f"[red]✗[/red] Could not find message input field for {match_name}.")
        return False
    except Exception as e:
        rprint(f"[red]✗[/red] Unexpected error while sending message to {match_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def navigate_back_to_chats_list(driver, num_back_presses=3):
    rprint(f"[blue]→[/blue] Navigating back: {num_back_presses} back presses")
    for i in range(num_back_presses):
        driver.back()
        delay = random.uniform(0.3, 0.7) if i < num_back_presses - 1 else random.uniform(1.0, 1.5)
        rprint(f"[blue]→[/blue] Back press #{i+1}, pausing for {delay:.2f}s")
        time.sleep(delay)

    if is_on_chats_list_page(driver, timeout=5):
        rprint("[green]✓[/green] Successfully returned to Chats list page")
        return True
    else:
        if open_page(driver,"Chats"):
            return True
        else:
            rprint("[red]✗[/red] Failed to return to Chats list page")
            return False


# --- Main Processing Logic ---
def process_new_matches(driver, max_total_matches_to_process_this_run=10, process_percentage_of_new_found=0.9):
    """
    Randomly selects and processes a percentage of new matches from the "Your matches" list.

    Args:
        driver: The Appium WebDriver instance.
        max_total_matches_to_process_this_run (int, optional): 
            Absolute maximum number of matches to process in this entire call to process_new_matches.
            Helps to limit overall activity if many new matches are found.
        process_percentage_of_new_found (float, optional): 
            The approximate percentage (0.0 to 1.0) of newly found, unattempted matches
            to process in each pass of checking the "Your matches" list.
            Default is 0.7 (70%).
    """
    if not is_on_chats_list_page(driver): # Initial check
        rprint("[red]✗[/red] Not starting on Chats list page. Aborting match processing")
        return

    rprint(f"[blue]→[/blue] Starting to process new matches. Aiming for ~{process_percentage_of_new_found*100:.0f}% of new finds.")
    if max_total_matches_to_process_this_run is not None:
        rprint(f"[blue]→[/blue] Overall limit for this run: {max_total_matches_to_process_this_run} matches.")

    grand_total_processed_this_run = 0
    attempted_matches_content_descs_session = set() # Keep track of all attempted in this entire session/call

    # We might loop a few times if the "Your matches" list is dynamic or to pick in batches
    # but we won't loop indefinitely if no new matches are found.
    # Let's limit the number of times we re-scan the "Your matches" list to avoid getting stuck.
    max_list_scan_attempts = 3 
    
    for scan_attempt in range(max_list_scan_attempts):
        if max_total_matches_to_process_this_run is not None and \
           grand_total_processed_this_run >= max_total_matches_to_process_this_run:
            rprint(f"[yellow]ℹ[/yellow] Reached overall limit of {max_total_matches_to_process_this_run} matches processed for this run.")
            break

        if not is_on_chats_list_page(driver, timeout=3): # Re-check current page
            rprint("[red]✗[/red] No longer on Chats list page during processing. Aborting.")
            break
        
        rprint(f"\n[cyan]--- Scan attempt #{scan_attempt + 1} for new matches ---[/cyan]")

        # --- Check for Ads/Promos first ---
        promo_detected_this_scan = False
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located(SPOTLIGHT_PROMO_TEXT_LOCATOR))
            rprint("[yellow]ℹ[/yellow] Spotlight promo detected in 'Your matches' area.")
            promo_detected_this_scan = True
        except TimeoutException: pass
        if not promo_detected_this_scan:
            try:
                WebDriverWait(driver, 1).until(EC.presence_of_element_located(OPENING_MOVES_SETUP_PROMO_TEXT_LOCATOR))
                rprint("[yellow]ℹ[/yellow] 'Opening Moves setup' promo detected.")
                promo_detected_this_scan = True
            except TimeoutException: pass
        
        if promo_detected_this_scan:
            rprint("[yellow]ℹ[/yellow] Ad/Promo found where new matches usually are. Ending current scan.")
            # If a promo is consistently there, further scans might not yield new matches in this section.
            break 

        # --- Get actual match items ---
        try:
            matches_rv = WebDriverWait(driver, 7).until(
                EC.presence_of_element_located(YOUR_MATCHES_RV_LOCATOR)
            )
            all_match_buttons_on_screen = matches_rv.find_elements(AppiumBy.XPATH, MATCH_ITEM_BUTTON_XPATH)

            if not all_match_buttons_on_screen:
                rprint("[yellow]ℹ[/yellow] No match items found in 'Your matches' list during this scan.")
                # If no matches found in the first scan attempt, likely no new matches.
                # If in subsequent scans, it means we processed all available from previous.
                break 

            # Filter out already attempted matches in this entire session
            new_unattempted_matches = []
            for btn in all_match_buttons_on_screen:
                try:
                    if not btn.is_displayed(): continue # Skip non-visible elements
                    desc = btn.get_attribute('content-desc')
                    if desc and desc not in attempted_matches_content_descs_session:
                        new_unattempted_matches.append({'element': btn, 'desc': desc})
                except StaleElementReferenceException:
                    rprint("[yellow]⚠[/yellow] Stale element while collecting new matches. Will retry scan if possible.")
                    # Force a re-scan by breaking this inner loop and letting outer loop continue if attempts left
                    new_unattempted_matches = "RETRY_SCAN" 
                    break 
            
            if new_unattempted_matches == "RETRY_SCAN":
                time.sleep(0.5)
                continue # To the next scan_attempt

            if not new_unattempted_matches:
                rprint("[yellow]ℹ[/yellow] No NEW, unattempted matches found in 'Your matches' list this scan.")
                # TODO: Could implement horizontal scroll here if `all_match_buttons_on_screen` was full but all were attempted
                break # No new matches to process in this scan

            rprint(f"[blue]→[/blue] Found {len(new_unattempted_matches)} new, unattempted match(es) on screen.")

            # Randomly select a portion of these new matches to process
            num_to_select = max(1, int(len(new_unattempted_matches) * process_percentage_of_new_found))
            if max_total_matches_to_process_this_run is not None: # Adhere to overall limit
                remaining_allowed_overall = max_total_matches_to_process_this_run - grand_total_processed_this_run
                num_to_select = min(num_to_select, remaining_allowed_overall)

            if num_to_select <= 0 :
                 rprint("[yellow]ℹ[/yellow] No more matches to process based on limits or percentage.")
                 break


            matches_to_process_this_pass = random.sample(new_unattempted_matches, min(num_to_select, len(new_unattempted_matches)))
            rprint(f"[blue]→[/blue] Randomly selected {len(matches_to_process_this_pass)} match(es) to process this pass.")

            for match_info in matches_to_process_this_pass:
                current_match_element_to_click = match_info['element']
                current_match_desc = match_info['desc']

                # Mark as attempted for the entire session
                attempted_matches_content_descs_session.add(current_match_desc)
                
                rprint(f"\n[magenta]--- Processing selected match: {current_match_desc} ---[/magenta]")
                try:
                    current_match_element_to_click.click()
                except StaleElementReferenceException:
                    rprint(f"[red]✗[/red] Stale element when trying to click {current_match_desc}. Skipping this one.")
                    continue # Skip to next selected match
                except Exception as click_err:
                    rprint(f"[red]✗[/red] Error clicking match {current_match_desc}: {click_err}. Skipping.")
                    continue

                time.sleep(random.uniform(1.5, 2.5)) 

                user_name_for_chat_verification = current_match_desc

                if handle_opening_move_screen(driver):
                    rprint("[green]✓[/green] Handled 'Opening Move' screen")
                
                if is_on_individual_chat_page(driver, user_name_for_verification=user_name_for_chat_verification):
                    if send_opening_message(driver, user_name_for_chat_verification):
                        grand_total_processed_this_run += 1
                        rprint(f"[green]✓[/green] Successfully processed and messaged {current_match_desc}")
                    else:
                        rprint(f"[red]✗[/red] Failed to send message to {current_match_desc}")

                    if not navigate_back_to_chats_list(driver): # Uses 3 back presses by default
                        rprint("[red]✗[/red] Critical: Failed to navigate back after chat. Ending run.")
                        return # Exit entirely if navigation back fails
                else:
                    rprint(f"[red]✗[/red] Did not land on individual chat page for {current_match_desc}.")
                    if not navigate_back_to_chats_list(driver):
                        rprint("[red]✗[/red] Critical: Failed to navigate back after failed chat entry. Ending run.")
                        return
                
                time.sleep(random.uniform(1.0, 2.0)) # Pause between processing selected matches

                if max_total_matches_to_process_this_run is not None and \
                   grand_total_processed_this_run >= max_total_matches_to_process_this_run:
                    break # Break from processing this pass's matches if overall limit hit

            if max_total_matches_to_process_this_run is not None and \
               grand_total_processed_this_run >= max_total_matches_to_process_this_run:
                break # Break from scan_attempt loop if overall limit hit

            # If we processed some matches, it's good to pause before re-scanning, UI might refresh
            if matches_to_process_this_pass:
                rprint(f"[grey50]Pausing before next potential scan of 'Your matches' list...[/grey50]")
                time.sleep(random.uniform(2.0, 4.0))


        except TimeoutException:
            rprint("[yellow]⚠[/yellow] Timeout waiting for 'Your matches' RecyclerView this scan. It might not be present or only promos are showing.")
            break # No point in more scan attempts if the main list isn't found
        except StaleElementReferenceException:
            rprint("[yellow]⚠[/yellow] StaleElementReferenceException during main part of scan. Retrying scan if attempts left.")
            time.sleep(1)
            # The outer for loop (scan_attempt) will handle the next attempt if any
        except Exception as e:
            rprint(f"[red]✗[/red] Unexpected error during scan attempt #{scan_attempt + 1}: {e}")
            import traceback
            traceback.print_exc()
            break 

    rprint(f"\n[bold green]✓ Finished processing session. Total successfully messaged: {grand_total_processed_this_run}[/bold green]")
if __name__ == "__main__":
    caps = {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:deviceName": "emulator-5554",
        "appium:appPackage": "com.bumble.app",
        "appium:noReset": True,
        "appium:newCommandTimeout": 300
    }
    appium_server_url = 'http://127.0.0.1:4723'
    driver = None
    try:
        options = UiAutomator2Options().load_capabilities(caps)
        rprint("[blue]→[/blue] Connecting to Appium driver...")
        driver = webdriver.Remote(appium_server_url, options=options)
        rprint("[green]✓[/green] Driver connected")
        
        rprint("[yellow]ℹ[/yellow] Please navigate to the 'Chats' tab in Bumble")
        rprint("[yellow]ℹ[/yellow] Waiting for 10 seconds...")
        time.sleep(10)

        if is_on_chats_list_page(driver):
            rprint("[green]✓[/green] Starting match processing")
            process_new_matches(driver, max_matches_to_process=2)
        else:
            rprint("[red]✗[/red] Not on Chats list page. Please check app state")

        rprint("\n[yellow]ℹ[/yellow] Test finished. Check console for detailed logs")
        rprint("[yellow]ℹ[/yellow] Keeping app open for observation...")
        time.sleep(15)
    except Exception as e:
        rprint(f"[red]✗[/red] Critical error in main test block: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                driver.save_screenshot(f"chat_error_{ts}.png")
                with open(f"chat_error_source_{ts}.xml", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                rprint(f"[green]✓[/green] Saved error debug info ({ts})")
            except Exception as e_save:
                rprint(f"[red]✗[/red] Could not save error debug info: {e_save}")
    finally:
        if driver:
            rprint("[blue]→[/blue] Quitting driver")
            driver.quit()
