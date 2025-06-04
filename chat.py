# chat.py

import time
import random
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from rich import print as rprint
from rich.console import Console

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
CHAT_SEND_BUTTON_LOCATOR = (AppiumBy.XPATH, "//*[@content-desc='Send' and @clickable='true']") # Common pattern
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
    rprint(f"[blue]→[/blue] Attempting to send opening message to {match_name}")
    try:
        message_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(CHAT_MESSAGE_INPUT_LOCATOR)
        )

        first_name = match_name.split(',')[0].split(' ')[0]
        messages = [
            f"Hey {first_name}! How's your day going? 😊",
            f"Hi {first_name}! Nice to match with you. What are you up to?",
            f"Hello {first_name}! 👋 Hope you're having a good one.",
            f"Hey {first_name}, pleasure to connect!",
        ]
        message_to_send = random.choice(messages)

        message_input.click()
        time.sleep(0.5)

        current_text_in_input = message_input.text
        if current_text_in_input and current_text_in_input.lower() == "aa":
            rprint("[yellow]ℹ[/yellow] Clearing default input text")
            message_input.clear()
            time.sleep(0.3)

        rprint(f"[blue]→[/blue] Sending message: '{message_to_send}'")
        message_input.send_keys(message_to_send)
        
        time.sleep(random.uniform(0.8, 1.8))

        final_typed_text = message_input.text
        if final_typed_text != message_to_send:
            rprint(f"[yellow]⚠[/yellow] Text mismatch - Expected: '{message_to_send}', Got: '{final_typed_text}'")
            if not message_to_send.lower().startswith(final_typed_text.lower()[:len(message_to_send)-5]) and \
               not final_typed_text.lower().startswith(message_to_send.lower()[:len(final_typed_text)-5]):
                rprint("[red]✗[/red] Significant text mismatch detected")

        try:
            send_button = WebDriverWait(driver, 7).until(
                EC.element_to_be_clickable(CHAT_SEND_BUTTON_LOCATOR)
            )
            rprint("[green]✓[/green] Message sent successfully")
        except TimeoutException:
            rprint("[red]✗[/red] Send button not found or not clickable")
            return False

        time.sleep(random.uniform(1.0, 2.5))
        return True

    except TimeoutException:
        rprint(f"[red]✗[/red] Could not find message input for {match_name}")
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
        rprint("[red]✗[/red] Failed to return to Chats list page")
        return False


# --- Main Processing Logic ---
def process_new_matches(driver, max_matches_to_process=None):
    if not is_on_chats_list_page(driver):
        rprint("[red]✗[/red] Not starting on Chats list page. Aborting match processing")
        return

    rprint("[blue]→[/blue] Starting to process new matches from 'Your matches' list")
    processed_count = 0
    attempted_matches_content_descs = set()

    while True:
        promo_detected = False
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located(SPOTLIGHT_PROMO_TEXT_LOCATOR))
            rprint("[yellow]ℹ[/yellow] Spotlight promo detected in 'Your matches' area")
            promo_detected = True
        except TimeoutException:
            pass

        if not promo_detected:
            try:
                WebDriverWait(driver, 1).until(EC.presence_of_element_located(OPENING_MOVES_SETUP_PROMO_TEXT_LOCATOR))
                rprint("[yellow]ℹ[/yellow] 'Opening Moves setup' promo detected")
                promo_detected = True
            except TimeoutException:
                pass

        if promo_detected:
            rprint("[yellow]ℹ[/yellow] Ad/Promo found instead of new matches. Concluding processing")
            break

        if max_matches_to_process is not None and processed_count >= max_matches_to_process:
            rprint(f"[yellow]ℹ[/yellow] Reached limit of {max_matches_to_process} matches to process")
            break

        current_match_element_to_click = None
        current_match_desc = None

        try:
            matches_rv = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(YOUR_MATCHES_RV_LOCATOR)
            )
            match_buttons = matches_rv.find_elements(AppiumBy.XPATH, MATCH_ITEM_BUTTON_XPATH)

            if not match_buttons:
                rprint("[yellow]ℹ[/yellow] No match items found in 'Your matches' list")
                break

            for i, match_button in enumerate(match_buttons):
                try:
                    desc = match_button.get_attribute('content-desc')
                    if desc and desc not in attempted_matches_content_descs:
                        current_match_element_to_click = match_button
                        current_match_desc = desc
                        rprint(f"[blue]→[/blue] Found new match to process: {current_match_desc}")
                        break
                except StaleElementReferenceException:
                    rprint("[yellow]⚠[/yellow] Stale element encountered, will re-fetch list")
                    current_match_element_to_click = "RETRY_LIST_FETCH"
                    break
            
            if current_match_element_to_click == "RETRY_LIST_FETCH":
                time.sleep(0.5)
                continue

            if not current_match_element_to_click:
                rprint("[yellow]ℹ[/yellow] No new, unattempted matches found")
                break

            attempted_matches_content_descs.add(current_match_desc)
            
            rprint(f"[blue]→[/blue] Clicking match: {current_match_desc}")
            current_match_element_to_click.click()
            time.sleep(random.uniform(1.5, 2.5))

            user_name_for_chat_verification = current_match_desc

            if handle_opening_move_screen(driver):
                rprint("[green]✓[/green] Handled 'Opening Move' screen")
            else:
                rprint("[yellow]ℹ[/yellow] 'Opening Move' screen not detected")

            if is_on_individual_chat_page(driver, user_name_for_verification=user_name_for_chat_verification):
                if send_opening_message(driver, user_name_for_chat_verification):
                    processed_count += 1
                    rprint(f"[green]✓[/green] Successfully processed {user_name_for_chat_verification}")
                else:
                    rprint(f"[red]✗[/red] Failed to send message to {user_name_for_chat_verification}")

                if not navigate_back_to_chats_list(driver):
                    return
            else:
                rprint(f"[red]✗[/red] Did not land on individual chat page for {current_match_desc}")
                if not navigate_back_to_chats_list(driver):
                    return
            
            time.sleep(random.uniform(1.0, 2.0))

        except TimeoutException:
            rprint("[red]✗[/red] Timeout waiting for 'Your matches' list")
            break
        except StaleElementReferenceException:
            rprint("[yellow]⚠[/yellow] StaleElementReferenceException, retrying list fetch")
            time.sleep(1)
            continue
        except Exception as e:
            rprint(f"[red]✗[/red] Unexpected error in process_new_matches: {e}")
            import traceback
            traceback.print_exc()
            break

    rprint(f"[green]✓[/green] Finished processing. Total successfully messaged: {processed_count}")

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
