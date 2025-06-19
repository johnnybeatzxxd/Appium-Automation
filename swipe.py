import random
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException # Added TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helper import handle_adjust_filters_prompt
from helper import adjust_age_filter_and_apply
from helper import get_screen_dimensions
from rich import print as rprint

# Using a distinctive text on the ad screen for initial detection
PREMIUM_AD_IDENTIFIER_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[@text=\"Find who you're looking for, faster\"]")

# The "Maybe later" button is a clickable View containing a TextView with text "Maybe later"
PREMIUM_AD_MAYBE_LATER_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.view.View[@clickable='true' and .//android.widget.TextView[@text=\"Maybe later\"]]"
)
# --- Locators for the SuperSwipe Info Popup ---
# Using a distinctive text on the popup for initial detection
SUPERSWIPE_POPUP_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[@text=\"Supercharge your chance to match\"]"
)

# The "Got it" button is a clickable View containing a TextView with text "Got it"
SUPERSWIPE_POPUP_GOT_IT_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.view.View[@clickable='true' and .//android.widget.TextView[@text=\"Got it\"]]"
)

# Alternative: Close button at the top right of the popup content area
SUPERSWIPE_POPUP_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.XPATH,
    "//android.widget.ImageView[@content-desc='Close' and @clickable='true']"
)

FIRST_MOVE_SCREEN_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[contains(@text, \"It's time to\") and contains(@text, \"make your move\")]"
) 
FIRST_MOVE_SCREEN_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.ID, "com.bumble.app:id/navbar_button_navigation"
)

ITS_A_MATCH_SCREEN_IDENTIFIER_TEXT = (AppiumBy.XPATH, "//*[@resource-id='com.bumble.app:id/match_explanationTitle' and @text='What a match!']")
# Or by container ID if more stable:
# ITS_A_MATCH_SCREEN_CONTAINER_ID = (AppiumBy.ID, "com.bumble.app:id/mutualAttraction_topContainer")

# "Opening Moves" info box elements (if present on the "It's a Match!" screen)
OPENING_MOVES_INFO_BOX_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[@text='Kick things off with Opening Moves']")
OPENING_MOVES_INFO_BOX_GOT_IT_BUTTON_LOCATOR = (
    AppiumBy.XPATH,
    "//androidx.compose.ui.platform.ComposeView[.//android.widget.TextView[@text='Kick things off with Opening Moves']]//android.view.View[@clickable='true' and .//android.widget.TextView[@text='Got it']]"
) # This XPath is more specific to the "Got it" within the "Opening Moves" box

# Main "Close" button for the entire "It's a Match!" screen (top left)
ITS_A_MATCH_MAIN_CLOSE_BUTTON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/match_close")

MATCH_SCREEN_MINI_COMPOSER_INPUT_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/composerMini_text")
MATCH_SCREEN_MINI_COMPOSER_SEND_ICON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/composerMini_icon")

BEST_PHOTO_POPUP_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[@text='Put your best photo first']"
)
# The "Save and close" button
BEST_PHOTO_POPUP_SAVE_AND_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.Button[@text='Save and close']"
)

PROFILE_CARD_LOADED_INDICATOR_XPATH = (
    "//android.widget.FrameLayout[@resource-id='com.bumble.app:id/encountersStackContainer']"
    "//androidx.compose.ui.platform.ComposeView/android.view.View/android.view.View[1]"
    "//android.widget.TextView" # Looking for any TextView as a sign of content on the card
)

NAV_BAR_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/mainApp_navigationTabBar")
# Bumble logo, typical of the swipe screen
NAVBAR_LOGO_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/navbar_logo")

def wait_for_profile_to_load(driver, max_retries=5, wait_per_retry_sec=3, load_timeout_sec=5):
    """
    Checks if the app is on the Discover/swipe page and appears to be stuck loading profiles.
    It waits for a profile card indicator to appear.

    Args:
        driver: The Appium WebDriver instance.
        max_retries (int): How many times to check for a loaded profile.
        wait_per_retry_sec (int): How long to sleep between retries.
        load_timeout_sec (int): How long to wait for the profile card indicator in each attempt.

    Returns:
        bool: True if a profile eventually loads (or was already loaded), 
              False if it seems stuck loading after all retries.
    """
    rprint("[yellow]Checking if Discover page is loading profiles...[/yellow]")

    for attempt in range(max_retries):
        try:
            # 1. First, confirm we are on a page that *should* show profiles (e.g., Discover page)
            #    by checking for persistent UI elements like the nav bar and logo.
            WebDriverWait(driver, 2).until(EC.presence_of_element_located(NAV_BAR_LOCATOR))
            WebDriverWait(driver, 2).until(EC.presence_of_element_located(NAVBAR_LOGO_LOCATOR))
            # rprint(f"[grey50]Attempt {attempt + 1}/{max_retries}: Discover page elements present.[/grey50]")

            # 2. Now, try to find an indicator that a profile CARD is actually loaded and visible.
            #    If this is found, loading is complete (or was never stuck).
            WebDriverWait(driver, load_timeout_sec).until(
                EC.presence_of_element_located((AppiumBy.XPATH, PROFILE_CARD_LOADED_INDICATOR_XPATH))
                # Or use your more specific PROFILE_CARD_USER_NAME_LOCATOR if you define it
            )
            rprint("[green]Profile card appears to be loaded.[/green]")
            return True # Profile loaded

        except TimeoutException:
            # This TimeoutException means either the Discover page elements weren't found (unlikely if called during swiping)
            # OR the PROFILE_CARD_LOADED_INDICATOR was not found within 'load_timeout_sec'.
            rprint(f"[orange_red1]Attempt {attempt + 1}/{max_retries}: Profile card not detected within {load_timeout_sec}s. App might be loading or no profiles.[/orange_red1]")
            if attempt < max_retries - 1:
                rprint(f"[yellow]Waiting for {wait_per_retry_sec}s before next check...[/yellow]")
                time.sleep(wait_per_retry_sec)
            else:
                rprint(f"[red]Max retries ({max_retries}) reached. Assuming profiles are not loading or none available currently.[/red]")
                return False # Stuck loading or no profiles after all retries
        except Exception as e:
            rprint(f"[red]An unexpected error occurred while checking for profile load: {e}[/red]")
            return False # Exit on other errors

    return False # Should be covered by the loop's else, but as a fallback.

def handle_best_photo_popup(driver, timeout=3):
    """
    Checks for the "Best Photo" feature popup and clicks "Save and close".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the popup was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the popup.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(BEST_PHOTO_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        rprint("[yellow]'Best Photo' popup detected ('Put your best photo first').[/yellow]")

        # 2. If the popup is detected, find and click the "Save and close" button.
        save_and_close_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(BEST_PHOTO_POPUP_SAVE_AND_CLOSE_BUTTON_LOCATOR)
        )
        
        action_delay = random.uniform(0.4, 0.8)
        rprint(f"[yellow]Clicking 'Save and close' button in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        save_and_close_button.click()
        rprint("[green]Clicked 'Save and close' on the 'Best Photo' popup.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss and settle
        return True # Popup was handled

    except TimeoutException:
        # The popup was not found within the timeout period. This is normal.
        # rprint("[grey50]Debug: 'Best Photo' popup not found.[/grey50]")
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the 'Best Photo' popup: {e}[/red]")
        # try:
        #     rprint(f"[grey37]Page source on 'Best Photo' popup error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False


def handle_they_saw_you_premium_popup(driver, timeout=1):
    """
    Checks for the "They saw you, they're into you" Premium upsell popup
    and clicks "Maybe later".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the ad was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of a distinctive element of the ad.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(THEY_SAW_YOU_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        rprint("[yellow]'They saw you, they're into you' Premium popup detected.[/yellow]")

        # 2. If the ad is detected, try to click the "Maybe later" button.
        try:
            maybe_later_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(THEY_SAW_YOU_POPUP_MAYBE_LATER_BUTTON_LOCATOR)
            )
            
            action_delay = random.uniform(0.3, 0.6)
            rprint(f"[yellow]Clicking 'Maybe later' in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            
            maybe_later_button.click()
            rprint("[green]Clicked 'Maybe later' on 'They saw you' Premium popup.[/green]")

        except TimeoutException:
            rprint("[yellow]'Maybe later' button not found or clickable. Trying 'Close' button as fallback...[/yellow]")
            # Fallback to the "Close" button (top left)
            # Ensure THEY_SAW_YOU_POPUP_CLOSE_BUTTON_LOCATOR is accurate for this specific popup's close button.
            # The XML structure for the close button is: clickable View -> (View content-desc="Close", Button)
            # We target the clickable View that contains the "Close" element.
            # Let's refine the close button XPath for this specific structure:
            actual_close_button_locator = (AppiumBy.XPATH, "//android.view.View[@clickable='true' and .//android.view.View[@content-desc='Close']]")
            # This looks for a clickable View that has a descendant View with content-desc="Close".

            close_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(actual_close_button_locator)
            )
            action_delay = random.uniform(0.4, 1.1)
            rprint(f"[yellow]Clicking top 'Close' button in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            close_button.click()
            rprint("[green]Clicked top 'Close' button on 'They saw you' Premium popup.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss the popup and settle
        
        return True # Ad was handled

    except TimeoutException:
        # The ad was not found within the timeout period. This is normal.
        # rprint("[grey50]Debug: 'They saw you' Premium popup not found.[/grey50]")
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the 'They saw you' Premium popup: {e}[/red]")
        # try:
        #     rprint(f"[grey37]Page source on 'They saw you' error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False



def handle_its_a_match_and_opening_moves_popup(driver, timeout=1,fallback_to_close=True):
    """
    Checks for the "It's a Match!" screen. If found:
    1. Handles the "Opening Moves" info box (if present).
    2. Types "hi" into the mini composer and sends it.
    3. Navigates back (e.g., to swiping).

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for elements.
        fallback_to_close (bool): If True, attempts to close the match screen if sending "hi" fails.

    Returns:
        bool: True if the "It's a Match!" screen was detected and an action (send or close) was performed, False otherwise.
    """
    try:
        # 1. Check for the main "It's a Match!" screen.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(ITS_A_MATCH_SCREEN_IDENTIFIER_TEXT)
        )
        rprint("[yellow]'It's a Match!' screen detected.[/yellow]")
        
        action_taken_on_match_screen = False # Flag to track if we did anything

        # 2. (Optional) Try to click "Got it" for the "Opening Moves" info box if it's present.
        try:
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located(OPENING_MOVES_INFO_BOX_TEXT_LOCATOR)
            )
            opening_moves_got_it_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable(OPENING_MOVES_INFO_BOX_GOT_IT_BUTTON_LOCATOR)
            )
            rprint(f"[yellow]Found 'Opening Moves' info box. Clicking 'Got it'...")
            opening_moves_got_it_button.click()
            rprint("[green]Clicked 'Got it' on 'Opening Moves' info box.[/green]")
            time.sleep(random.uniform(0.5, 1.0)) # Pause after this click
            action_taken_on_match_screen = True
        except TimeoutException:
            rprint("[grey50]Debug: 'Opening Moves' info box not found on 'It's a Match!' screen. Skipping its 'Got it'.[/grey50]")
        except Exception as e_om:
            rprint(f"[orange_red1]Minor error handling 'Opening Moves' info box: {e_om}. Proceeding.[/orange_red1]")

        # 3. Type "hi" into the mini composer and send.
        message_sent_successfully = False
        try:
            rprint("[yellow]Attempting to send 'hi' from 'It's a Match!' screen...[/yellow]")
            mini_composer_input = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(MATCH_SCREEN_MINI_COMPOSER_INPUT_LOCATOR)
            )
            
            mini_composer_input.click() # Focus the input
            time.sleep(0.3)
            
            # Clear if needed (e.g., if "Send a message..." is actual text, not just hint)
            if mini_composer_input.text.lower() == "send a message...":
                 mini_composer_input.clear()
                 time.sleep(0.2)

            mini_composer_input.send_keys("hey")
            rprint("[green]Typed 'hi' into mini composer.[/green]")
            time.sleep(random.uniform(0.5, 1.0)) # Pause after typing

            # The send icon becomes enabled after typing.
            send_icon = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(MATCH_SCREEN_MINI_COMPOSER_SEND_ICON_LOCATOR)
            )
            # Double check if it's actually enabled, though element_to_be_clickable should cover this
            if not send_icon.is_enabled():
                rprint("[orange_red1]Send icon found but reported as not enabled. Attempting click anyway.[/orange_red1]")
                # This might indicate an issue or a slight delay in UI update for enabled state.

            # send_icon.click()
            rprint("[green]Clicked send icon for 'hi' message.[/green]")
            # message_sent_successfully = True
            # action_taken_on_match_screen = True
            time.sleep(random.uniform(0.5, 1.0)) # Pause after sending

        except TimeoutException:
            rprint("[red]Failed to find mini composer elements or send message on 'It's a Match!' screen.[/red]")
        except Exception as e_send:
            rprint(f"[red]Error sending 'hi' from 'It's a Match!' screen: {e_send}[/red]")

        # 4. If sending "hi" failed AND fallback is enabled, try to close the screen.
        #    Or, if you ALWAYS want to close after sending, this logic changes.
        #    Current logic: Prioritize sending message. If that path fails, then consider closing.
        if not message_sent_successfully and fallback_to_close:
            rprint("[yellow]Sending 'hi' failed or was skipped. Attempting to close 'It's a Match!' screen as fallback.[/yellow]")
            try:
                main_close_button = WebDriverWait(driver, 2).until( # Shorter timeout for fallback close
                    EC.element_to_be_clickable(ITS_A_MATCH_MAIN_CLOSE_BUTTON_LOCATOR)
                )
                main_close_button.click()
                rprint("[green]Clicked main 'Close' button to dismiss 'It's a Match!' screen (fallback).[/green]")
                action_taken_on_match_screen = True
                time.sleep(random.uniform(1.2, 2.2))
            except Exception as e_close:
                rprint(f"[red]Failed to close 'It's a Match!' screen via 'Close' button during fallback: {e_close}[/red]")
                rprint("[orange_red1]Attempting system back as final fallback for 'It's a Match!' screen.[/orange_red1]")
                time.sleep(1.5)
                action_taken_on_match_screen = True # Assume back action did something

        elif message_sent_successfully:
            # If message was sent, we still need to get off this screen.
            # Typically, after sending from this mini-composer, the screen might auto-dismiss
            # or transition to the full chat. If it just stays on "It's a Match!", we need to close it.
            rprint("[grey50]Message sent from 'It's a Match!'. Performing system back to return to swiping.[/grey50]")
            time.sleep(random.uniform(0.3, 1.0))
            action_taken_on_match_screen = True


        return action_taken_on_match_screen # Return true if we interacted with the match screen

    except TimeoutException:
        # The "It's a Match!" screen itself was not found.
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the 'It's a Match!' screen: {e}[/red]")
        return False

def handle_first_move_info_screen(driver, timeout=1):

    """
    Checks for the "It's time to make your move" info screen and clicks the "Close" button.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the screen elements.

    Returns:
        bool: True if the screen was detected and "Close" was clicked, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the screen.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(FIRST_MOVE_SCREEN_IDENTIFIER_TEXT_LOCATOR)
        )
        rprint("[yellow]'First Move' info screen detected ('It's time to make your move').[/yellow]")

        # 2. If the screen is detected, find and click the "Close" button.
        close_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(FIRST_MOVE_SCREEN_CLOSE_BUTTON_LOCATOR)
        )
        
        action_delay = random.uniform(0.2, 0.6)
        rprint(f"[yellow]Clicking 'Close' button on 'First Move' info screen in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        close_button.click()
        rprint("[green]Clicked 'Close' on the 'First Move' info screen.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss and settle
        
        return True # Screen was handled

    except TimeoutException:
        # The screen was not found within the timeout period. This is normal.
        # rprint("[grey50]Debug: 'First Move' info screen not found.[/grey50]")
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the 'First Move' info screen: {e}[/red]")
        # try:
        #     rprint(f"[grey37]Page source on 'First Move' info screen error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False


def handle_superswipe_info_popup(driver, timeout=1):
    """
    Checks for the "SuperSwipe info/upsell" popup and clicks "Got it".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the popup was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the popup.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(SUPERSWIPE_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        rprint("[yellow]SuperSwipe info/upsell popup detected ('Supercharge your chance to match').[/yellow]")

        # 2. If the popup is detected, find and click the "Got it" button.
        #    We could also try the "Close" button if "Got it" fails, but "Got it" is usually the primary dismissal.
        try:
            got_it_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(SUPERSWIPE_POPUP_GOT_IT_BUTTON_LOCATOR)
            )
            
            action_delay = random.uniform(0.2, 0.6)
            rprint(f"[yellow]Clicking 'Got it' in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            
            got_it_button.click()
            rprint("[green]Clicked 'Got it' on the SuperSwipe info popup.[/green]")

        except TimeoutException:
            rprint("[yellow]'Got it' button not immediately found or clickable. Trying 'Close' button as fallback...[/yellow]")
            # Fallback to the "Close" button if "Got it" is not found/clickable
            close_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(SUPERSWIPE_POPUP_CLOSE_BUTTON_LOCATOR)
            )
            action_delay = random.uniform(0.4, 1.1)
            rprint(f"[yellow]Clicking 'Close' button in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            close_button.click()
            rprint("[green]Clicked 'Close' button on the SuperSwipe info popup.[/green]")
            
        # Add a pause after clicking to allow the UI to dismiss the popup and settle
        
        return True # Popup was handled

    except TimeoutException:
        # The popup was not found within the timeout period. This is normal.
        # rprint("[grey50]Debug: SuperSwipe info popup not found.[/grey50]")
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the SuperSwipe info popup: {e}[/red]")
        # try:
        #     rprint(f"[grey37]Page source on SuperSwipe info error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False
def handle_premium_ad_popup(driver, timeout=1):
    """
    Checks for the "Premium" upsell ad popup and clicks "Maybe later".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the ad was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of a distinctive element of the ad.
        #    Using WebDriverWait to ensure the element is present.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(PREMIUM_AD_IDENTIFIER_TEXT_LOCATOR)
        )
        rprint("[yellow]Premium ad popup detected ('Find who you're looking for, faster').[/yellow]")

        # 2. If the ad is detected, find and click the "Maybe later" button.
        maybe_later_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(PREMIUM_AD_MAYBE_LATER_BUTTON_LOCATOR)
        )
        
        # Add a small random delay for natural interaction
        action_delay = random.uniform(0.2, 0.8)
        rprint(f"[yellow]Clicking 'Maybe later' in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        maybe_later_button.click()
        rprint("[green]Clicked 'Maybe later' on the premium ad popup.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss the popup and settle
        
        return True # Ad was handled

    except TimeoutException:
        # The ad was not found within the timeout period. This is normal if it doesn't appear.
        # rprint("[grey50]Debug: Premium ad popup not found.[/grey50]") # Can be noisy
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the premium ad popup: {e}[/red]")
        # It's good to see the page source if an unexpected error occurs here
        # try:
        #     rprint(f"[grey37]Page source on premium ad error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False

def is_popup_present(driver):
    try:
        # Replace this with actual identifiers for the popup
        popup = driver.find_element(AppiumBy.XPATH, "//android.view.ViewGroup/android.view.View/android.view.View/android.view.View") 
        return True
    except NoSuchElementException:
        return False

def handle_interested_confirmation_popup(driver, timeout=1):
    """
    Checks for the "Interested?" confirmation popup and clicks "YES".
    This popup typically appears to confirm a right swipe action.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup to appear.

    Returns:
        bool: True if the popup was detected and "YES" was clicked, False otherwise.
    """
    # Locators based on the provided XML for the "Interested?" popup
    popup_panel_locator = (AppiumBy.ID, "com.bumble.app:id/parentPanel") # Main dialog panel
    yes_button_locator = (AppiumBy.ID, "android:id/button1") # Standard Android dialog "positive" button ID
    # More specific XPath for YES button if needed:
    # yes_button_locator_xpath = (AppیمBy.XPATH, "//android.widget.Button[@resource-id='android:id/button1' and @text='YES']")

    try:
        # 1. Check for the presence of the popup panel.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(popup_panel_locator)
        )
        # print("DEBUG: 'Interested?' popup panel detected.") # Optional debug

        # 2. If popup panel is found, find and click the "YES" button.
        yes_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(yes_button_locator)
        )
        
        # Add a small random delay before clicking to seem more natural
        action_delay = random.uniform(0.2, 0.5)
        rprint(f"[yellow]Popup 'Interested?' detected. Clicking YES in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        yes_button.click()
        rprint("[green]Clicked 'YES' on the 'Interested?' popup.[/green]")
        
        # Add a small random delay after clicking to allow UI to process
        return True # Popup was handled

    except TimeoutException:
        # The popup (or its YES button) was not found. This is normal if it doesn't appear.
        return False
    except Exception as e:
        rprint(f"[red]An error occurred while handling the 'Interested?' popup: {e}[/red]")
        return False


def vertical_scroll(driver, is_first_swipe=False):
    """
    Perform a vertical scroll to check profile details.
    
    Args:
        driver: Appium WebDriver instance
        is_first_swipe: If True, performs a longer initial scroll
    """
    # Reduced delay before vertical scroll (0.2-0.8 seconds)
    # time.sleep(random.uniform(0.2, 0.8))
    screen_width, screen_height = get_screen_dimensions(driver)
    if not screen_width or not screen_height:
        rprint("[red]Failed to get screen dimensions for vertical scroll. Aborting scroll.[/red]")
        return
    # Perform vertical scroll with increased range
    start_y = int(screen_height * random.uniform(0.50, 0.70))
    
    # Longer scroll for first swipe
    if is_first_swipe:
        scroll_distance = int(screen_height * random.uniform(0.40, 0.55))
    else:
        scroll_distance = int(screen_height * random.uniform(0.30, 0.45))
    end_y = start_y - scroll_distance
    
    # Ensure end_y is not negative (scrolling off the top)
    end_y = max(50, end_y) # Keep at least 50px from top

    # Start X: somewhere in the middle 30% to 70% of screen width
    start_x = int(screen_width * random.uniform(0.30, 0.70))
    
    rprint(f"[grey50]Vertical scroll: screen_h={screen_height}, start_y={start_y}, end_y={end_y}, start_x={start_x}[/grey50]")

    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    time.sleep(random.uniform(0.05, 0.15)) # Brief pause before action
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    num_points = random.randint(2, 4) # More intermediate points for smoother scroll
    duration_ms = random.randint(300, 600) # Total scroll duration in ms
    
    for i in range(num_points):
        progress = (i + 1) / num_points
        current_y = int(start_y + (end_y - start_y) * progress)
        # Slight horizontal variance during scroll
        current_x = int(start_x + random.randint(-int(screen_width*0.02), int(screen_width*0.02))) 
        current_x = max(0, min(screen_width -1, current_x)) # Boundary check for x

        actions.w3c_actions.pointer_action.move_to_location(current_x, current_y)
        # time.sleep per point can be derived from total duration
        time.sleep((duration_ms / 1000.0) / num_points * random.uniform(0.8, 1.2)) 
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, end_y) # Ensure final point is reached
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    rprint(f"[grey50]Vertical scroll performed from ({start_x},{start_y}) to ({start_x},{end_y}).[/grey50]")

def horizontal_swipe(driver, swipe_right=True):
    """
    Perform a single horizontal swipe, aiming for a faster, more decisive gesture.
    """
    screen_width, screen_height = get_screen_dimensions(driver)
    if not screen_width or not screen_height:
        rprint("[red]Failed to get screen dimensions for horizontal swipe. Aborting swipe.[/red]")
        return

    # Start Y: Middle portion of the screen, slightly more constrained.
    start_y_percentage = random.uniform(0.40, 0.60) # Centered vertically more
    start_y = int(screen_height * start_y_percentage)
    
    # Swipe distance: Keep it substantial (55% to 70% of screen width).
    # Slightly reduced the upper bound a bit from 75% to 70% to prevent overshooting if screen is small,
    # but the key is the speed and decisiveness.
    swipe_distance_percentage = random.uniform(0.55, 0.70) 
    swipe_distance = int(screen_width * swipe_distance_percentage)

    if swipe_right:
        # Start X: From left part of the screen (e.g., 15% to 25%) - start a bit more inwards
        start_x_percentage = random.uniform(0.15, 0.25)
        start_x = int(screen_width * start_x_percentage)
        end_x = start_x + swipe_distance
    else: # swipe_left
        # Start X: From right part of the screen (e.g., 75% to 85%) - start a bit more inwards
        start_x_percentage = random.uniform(0.75, 0.85)
        start_x = int(screen_width * start_x_percentage)
        end_x = start_x - swipe_distance

    # Ensure end_x stays well within screen bounds with a slightly larger margin
    end_x = max(int(screen_width * 0.08), min(int(screen_width * 0.92), end_x)) # 8% margin

    # Vertical variation at the end of the swipe - keep it moderate
    end_y_variation_percentage = random.uniform(-0.06, 0.06) # +/- 6% of screen height
    end_y = start_y + int(screen_height * end_y_variation_percentage)
    end_y = max(int(screen_height*0.20), min(int(screen_height*0.80), end_y)) # Keep Y within 20-80% to avoid edges
    
    rprint(f"[grey50]Horizontal swipe: screen_w={screen_width}, start_x={start_x} ({start_x_percentage*100:.1f}%), end_x={end_x}, dist_perc={swipe_distance_percentage*100:.1f}%[/grey50]")

    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    # Very minimal pause before action starts
    time.sleep(random.uniform(0.01, 0.05)) 
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    # --- Adjusting for speed and decisiveness ---
    # Fewer intermediate points, faster total duration for a "quicker flick"
    num_points = random.randint(2, 4) 
    duration_ms = random.randint(150, 350) # Target total swipe duration in ms (FASTER)

    # Create a list of points including the start and end
    points = [(start_x, start_y)]
    for i in range(1, num_points + 1):
        progress = i / (num_points + 1.0) # Ensure progress goes towards end point
        
        # For a more "natural" arc or fling, the intermediate points shouldn't be perfectly linear.
        # We can make the x-component progress faster initially or towards the end for a fling.
        # Simple approach: slightly accelerate progress for x
        fling_progress_x = progress ** 0.8 # Makes it move a bit faster initially on x-axis
        
        current_x = int(start_x + (end_x - start_x) * fling_progress_x)
        current_y = int(start_y + (end_y - start_y) * progress) # Y can move more linearly

        # Add less random jitter if we want a more direct, fast swipe
        current_x += random.randint(-int(screen_width*0.01), int(screen_width*0.01))
        current_y += random.randint(-int(screen_height*0.01), int(screen_height*0.01))
        
        current_x = max(0, min(screen_width -1, current_x))
        current_y = max(0, min(screen_height -1, current_y))
        points.append((current_x, current_y))
    
    # Add the final precise end point
    if points[-1] != (end_x, end_y): # Ensure the last point is the target
        points.append((end_x, end_y))

    # Perform the moves
    for k in range(1, len(points)): # Start from the second point in our list
        px, py = points[k]
        # The duration of each segment of the move
        segment_duration_s = (duration_ms / 1000.0) / (len(points)-1) 
        actions.w3c_actions.pointer_action.move_to_location(px, py)
        time.sleep(segment_duration_s * random.uniform(0.8, 1.2)) # Slight variation in segment timing
    
    # No need for an extra move_to_location if the loop handles the last point correctly.
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    
    swipe_dir = "RIGHT" if swipe_right else "LEFT"
    rprint(f"[grey50]Horizontal swipe {swipe_dir} performed (duration: ~{duration_ms}ms).[/grey50]")
    time.sleep(random.uniform(0.1, 0.3)) # Reduced pause after swipe from 0.2-0.6 to 0.1-0.3
def realistic_swipe(driver, right_swipe_probability=5, duration_minutes=5):
    """
    Perform realistic swipes on Bumble with profile checking behavior.
    
    Args:
        driver: Appium WebDriver instance
        right_swipe_probability: Probability of swiping right (0-10)
        duration_minutes: How long to run the swiping session
    """
    end_time = time.time() + (duration_minutes * 60)
    
    while time.time() < end_time:
        # Random delay between profiles (2-3 seconds)
        start_time = time.time()

        current_app = driver.current_package
        if current_app != "com.bumble.app":
            rprint("[bold red]The app just closed![/bold red]")
            return


        if handle_interested_confirmation_popup(driver,0):
            rprint("[green]Handled 'Interested?' popup. Moving to next profile cycle.[/green]")
            time.sleep(random.uniform(0.5, 1.5)) # Pause after handling
            continue # Restart loop for the next profile evaluation

        rprint(f"[grey50]Time taken for interested confirmation popup check: {time.time() - start_time:.3f} seconds[/grey50]")
        # 2. Handle "Premium Ad" Popup (NEW)
        start_time = time.time()
        if handle_premium_ad_popup(driver,0): # Call the new handler
            # Log already in handle_premium_ad_popup
            # This popup usually dismisses to continue swiping, so we 'continue' the loop.
            continue
        rprint(f"[grey50]Time taken for premium ad popup check: {time.time() - start_time:.3f} seconds[/grey50]")

        start_time = time.time()
        if handle_superswipe_info_popup(driver,0): # Call the new handler
            # This popup usually dismisses to continue swiping.
            continue
        rprint(f"[grey50]Time taken for superswipe info popup check: {time.time() - start_time:.3f} seconds[/grey50]")

        start_time = time.time()
        if handle_its_a_match_and_opening_moves_popup(driver,0):
            continue 

        rprint(f"[grey50]Time taken for its a match popup check: {time.time() - start_time:.3f} seconds[/grey50]")

        start_time = time.time()
        if handle_first_move_info_screen(driver,0):
            # This screen dismissal usually returns to swiping.
            continue
        
        rprint(f"[grey50]Time taken for first move info screen check: {time.time() - start_time:.3f} seconds[/grey50]")

        # if handle_they_saw_you_premium_popup(driver):
        #     # This popup dismissal should return to swiping.
        #     continue

        start_time = time.time()
        if handle_first_move_info_screen(driver,0):
            # This screen dismissal usually returns to swiping.
            continue
        
        rprint(f"[grey50]Time taken for second first move info screen check: {time.time() - start_time:.3f} seconds[/grey50]")

        start_time = time.time()
        if handle_best_photo_popup(driver, timeout=0):
            continue
        rprint(f"[grey50]Time taken for best photo popup screen check: {time.time() - start_time:.3f} seconds[/grey50]")

        start_time = time.time()
        if handle_adjust_filters_prompt(driver,0): # Uses internal timeout
            rprint(f"[grey50]Time taken for adjust filters prompt check: {time.time() - start_time:.3f} seconds[/grey50]")
            rprint("[yellow]'Adjust filters' prompt appeared. Attempting to modify filters.[/yellow]")
            if adjust_age_filter_and_apply(driver): # Uses internal timeout
                rprint("[green]Age filter adjusted. Continuing swipe session.[/green]")
                time.sleep(random.uniform(1.0, 2.0)) # Pause for UI to settle
            else:
                rprint("[red]Failed to adjust age filter. Stopping swipe session.[/red]")
                return # Critical failure
            continue # Restart loop

        # 3. "Out of likes" or other critical blocking popups
        # IMPORTANT: Ensure is_popup_present uses SPECIFIC locators for the "out of likes" popup.
        start_time = time.time()
        if is_popup_present(driver): 
            rprint("[red]Critical popup (likely 'Out of likes') detected by is_popup_present. Stopping swipe session.[/red]")
            return # Stop swiping
        
        rprint(f"[grey50]Time taken for critical popup check: {time.time() - start_time:.3f} seconds[/grey50]")

        if not wait_for_profile_to_load(driver, max_retries=5, wait_per_retry_sec=3, load_timeout_sec=0):
            rprint("[bold red]Profiles are not loading after multiple checks. Ending swipe attempts for now.[/bold red]")
            # Decide what to do:
            # Option 1: End the entire realistic_swipe session
            return 
        # time.sleep(random.uniform(0, 2))
        
        # 60% chance to check profile details
        if random.randint(1, 10) <= 6:
            # Random number of vertical scrolls (2-4)
            num_scrolls = random.randint(2, 4)
            
            for i in range(num_scrolls):
                # First swipe is longer
                vertical_scroll(driver, is_first_swipe=(i == 0))
        
        # Perform horizontal swipe
        swipe_right = random.randint(1, 10) <= right_swipe_probability
        horizontal_swipe(driver, swipe_right)

if __name__ == "__main__":
    # Test configuration
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
    from appium.options.android import UiAutomator2Options
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.platform_version = "13"
    options.device_name = "RZ8W90Q3Q2A"
    options.automation_name = "UiAutomator2"
    options.app_package = "com.bumble.app"
    # options.app_activity = "com.bumble.app.ui.screenstories.ScreenStoryBlockersActivity"
    options.no_reset = True
    options.uiautomator2_server_install_timeout = 220000
    
    APPIUM_SERVER_URL = "http://127.0.0.1:4723"
    # Your Appium server configuration
    try:
        # Initialize the driver
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        
        # Wait for app to load
        time.sleep(5)
        
        rprint("[yellow]Testing vertical scroll...[/yellow]")
        # Test vertical scroll
        vertical_scroll(driver, is_first_swipe=True)  # Test first swipe
        time.sleep(2)
        vertical_scroll(driver, is_first_swipe=False)  # Test normal swipe
        time.sleep(2)
        
        rprint("[yellow]Testing horizontal swipes...[/yellow]")
        # Test horizontal swipes
        horizontal_swipe(driver, swipe_right=True)  # Test right swipe
        time.sleep(2)
        horizontal_swipe(driver, swipe_right=False)  # Test left swipe
        
        rprint("[green]Tests completed successfully![/green]")
        
    except Exception as e:
        rprint(f"[red]An error occurred: {str(e)}[/red]")
    
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()
