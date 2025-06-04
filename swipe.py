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
def is_popup_present(driver):
    try:
        # Replace this with actual identifiers for the popup
        popup = driver.find_element(AppiumBy.XPATH, "//android.view.ViewGroup/android.view.View/android.view.View/android.view.View") 
        return True
    except NoSuchElementException:
        return False
def handle_interested_confirmation_popup(driver, timeout=3):
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
        action_delay = random.uniform(0.4, 1.2)
        print(f"Popup 'Interested?' detected. Clicking YES in {action_delay:.2f} seconds...")
        time.sleep(action_delay)
        
        yes_button.click()
        print("Clicked 'YES' on the 'Interested?' popup.")
        
        # Add a small random delay after clicking to allow UI to process
        time.sleep(random.uniform(0.3, 0.8))
        
        return True # Popup was handled

    except TimeoutException:
        # The popup (or its YES button) was not found. This is normal if it doesn't appear.
        return False
    except Exception as e:
        print(f"An error occurred while handling the 'Interested?' popup: {e}")
        return False


def vertical_scroll(driver, is_first_swipe=False):
    """
    Perform a vertical scroll to check profile details.
    
    Args:
        driver: Appium WebDriver instance
        is_first_swipe: If True, performs a longer initial scroll
    """
    # Reduced delay before vertical scroll (0.2-0.8 seconds)
    time.sleep(random.uniform(0.2, 0.8))
    
    # Perform vertical scroll with increased range
    start_y = random.randint(1000, 1400)
    
    # Longer scroll for first swipe
    if is_first_swipe:
        end_y = start_y - random.randint(800, 1100)  # Longer initial scroll
    else:
        end_y = start_y - random.randint(600, 900)  # Normal scroll distance
    
    start_x = random.randint(300, 700)
    
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    # Reduced delay before starting scroll
    time.sleep(random.uniform(0.05, 0.15))
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    # Add intermediate points for natural movement
    num_points = random.randint(2, 3)  # Reduced points for faster scroll
    for i in range(num_points):
        progress = (i + 1) / num_points
        current_y = start_y + (end_y - start_y) * progress
        current_x = start_x + random.randint(-15, 15)
        actions.w3c_actions.pointer_action.move_to_location(current_x, current_y)
        time.sleep(random.uniform(0.02, 0.08))  # Reduced delay between points
    
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    
    # Reduced delay after vertical scroll (0.3-1.2 seconds)
    time.sleep(random.uniform(0.3, 1.2))

def horizontal_swipe(driver, swipe_right=True):
    """
    Perform a single horizontal swipe.
    
    Args:
        driver: Appium WebDriver instance
        swipe_right: If True, swipes right; if False, swipes left
    """
    start_x = random.randint(200, 800)
    start_y = random.randint(900, 1500)
    
    # Calculate end position with increased distance
    if swipe_right:
        end_x = start_x + random.randint(500, 800)  # Increased right swipe distance
    else:
        end_x = start_x - random.randint(500, 800)  # Increased left swipe distance
    
    # Add slight vertical variation to end position
    end_y = start_y + random.randint(-150, 150)  # Increased vertical variation
    
    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    # Minimal delay before horizontal swipe
    time.sleep(random.uniform(0.02, 0.08))
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    # Add intermediate points for more natural movement
    num_points = random.randint(2, 3)  # Reduced points for faster swipe
    for i in range(num_points):
        progress = (i + 1) / num_points
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        # Add more random variation for natural movement
        current_x += random.randint(-20, 20)
        current_y += random.randint(-20, 20)
        actions.w3c_actions.pointer_action.move_to_location(current_x, current_y)
        time.sleep(random.uniform(0.01, 0.04))  # Very short delay between points
    
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    
    # Reduced delay after horizontal swipe (0.3-0.8 seconds)
    time.sleep(random.uniform(0.3, 0.8))

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
        if handle_interested_confirmation_popup(driver):
            print("Handled 'Interested?' popup. Moving to next profile cycle.")
            time.sleep(random.uniform(0.5, 1.5)) # Pause after handling
            continue # Restart loop for the next profile evaluation


        if handle_adjust_filters_prompt(driver): # Uses internal timeout
            print("'Adjust filters' prompt appeared. Attempting to modify filters.")
            if adjust_age_filter_and_apply(driver): # Uses internal timeout
                print("Age filter adjusted. Continuing swipe session.")
                time.sleep(random.uniform(1.0, 2.0)) # Pause for UI to settle
            else:
                print("Failed to adjust age filter. Stopping swipe session.")
                return # Critical failure
            continue # Restart loop

        # 3. "Out of likes" or other critical blocking popups
        # IMPORTANT: Ensure is_popup_present uses SPECIFIC locators for the "out of likes" popup.
        if is_popup_present(driver): 
            print("Critical popup (likely 'Out of likes') detected by is_popup_present. Stopping swipe session.")
            return # Stop swiping

        time.sleep(random.uniform(2, 3))
        
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
        
        print("Testing vertical scroll...")
        # Test vertical scroll
        vertical_scroll(driver, is_first_swipe=True)  # Test first swipe
        time.sleep(2)
        vertical_scroll(driver, is_first_swipe=False)  # Test normal swipe
        time.sleep(2)
        
        print("Testing horizontal swipes...")
        # Test horizontal swipes
        horizontal_swipe(driver, swipe_right=True)  # Test right swipe
        time.sleep(2)
        horizontal_swipe(driver, swipe_right=False)  # Test left swipe
        
        print("Tests completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()
