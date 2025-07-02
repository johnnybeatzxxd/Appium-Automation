from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich import print as rprint
import time 
import random
import logging

log = rprint
NAV_BAR_ID = "com.bumble.app:id/mainApp_navigationTabBar" # Define as a constant

def get_screen_dimensions(driver):
    """Gets the current screen width and height."""
    try:
        window_size = driver.get_window_size()
        width = window_size.get('width')
        height = window_size.get('height')
        if width is None or height is None:
            print("WARNING: Could not get window dimensions, driver.get_window_size() returned None for width/height.")
            return None, None # Or raise an error, or return defaults
        return int(width), int(height)
    except Exception as e:
        print(f"Error getting screen dimensions: {e}")
        return None, None
def handle_adjust_filters_prompt(driver, timeout=3):
    """
    Checks for the "Adjust your filters" prompt (out of nearby profiles) and clicks the button.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for elements to appear.

    Returns:
        bool: True if the prompt was detected and handled, False otherwise.
    """
    # Define locators based on the XML
    # Using a more specific text that's less likely to appear elsewhere by chance
    identifier_text_locator = (AppiumBy.XPATH, '//android.widget.TextView[contains(@text, "You’ve seen everyone nearby")]')
    adjust_button_text_locator = (AppiumBy.XPATH, '//android.widget.TextView[@text="Adjust your filters"]')
    
    # More robust locator for the clickable button container:
    adjust_button_clickable_container_locator = (AppiumBy.XPATH, "//android.view.View[@clickable='true' and .//android.widget.TextView[@text='Adjust your filters']]")


    try:
        # 1. Check for the presence of the identifying text. Use a short explicit wait.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(identifier_text_locator)
        )
        log("[green]Detected 'Adjust your filters' prompt (Out of nearby profiles).[/green]")

        # 2. If identifying text is found, find and click the "Adjust your filters" button.
        #    It's better to click the clickable container View.
        adjust_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(adjust_button_clickable_container_locator)
        )
        adjust_button.click()
        log("[green]Clicked 'Adjust your filters' button.[/green]")
        
        # Optional: Add a small delay to allow the UI to transition to the filter screen
        time.sleep(2) 
        
        return True # Prompt was handled

    except TimeoutException:
        # The prompt was not found within the timeout period.
        # print("Debug: 'Adjust filters' prompt not found.") # Usually not needed if it's one of many checks
        return False
    except NoSuchElementException: # Should be caught by TimeoutException with WebDriverWait
        log("[red]Error: Element not found while trying to handle 'Adjust filters' prompt (NoSuchElementException).[/red]")
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling 'Adjust your filters' prompt: {e}[/red]")
        return False

def adjust_age_filter_and_apply(driver, timeout=15):

    """
    Adjusts the 'Higher age' slider to a high, but not absolute maximum, random value
    and clicks 'Apply'.
    Assumes the driver is already on the filter settings page where the age slider is visible.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for elements.

    Returns:
        bool: True if the age filter was adjusted and 'Apply' was clicked, False otherwise.
    """
    log("[yellow]Attempting to adjust age filter to a high random value and apply...[/yellow]")

    higher_age_thumb_locator = (AppiumBy.XPATH, '//com.badoo.mobile.component.rangebar.RangeBarItem[@content-desc="Higher age"]')
    slider_track_locator = (AppiumBy.ID, "com.bumble.app:id/range_bar_item")
    apply_button_locator = (
        AppiumBy.XPATH,
        "//android.widget.Button[contains(@text, 'Apply') or contains(@text, 'APPLY')] | "
        "//android.widget.TextView[@clickable='true' and (contains(@text, 'Apply') or contains(@text, 'APPLY'))] | "
        "//android.view.View[@clickable='true' and .//android.widget.TextView[contains(@text, 'Apply') or contains(@text, 'APPLY')]]"
    )

    try:
        log("[yellow]Locating age slider elements...[/yellow]")
        higher_age_thumb = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(higher_age_thumb_locator)
        )
        slider_track = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(slider_track_locator)
        )
        log("[green]Age slider elements located.[/green]")

        thumb_location = higher_age_thumb.location
        thumb_size = higher_age_thumb.size
        track_location = slider_track.location
        track_size = slider_track.size

        start_x = thumb_location['x'] + thumb_size['width'] // 2
        start_y = thumb_location['y'] + thumb_size['height'] // 2

        # --- REVISED LOGIC FOR TARGET X ---
        # Calculate the x-coordinate for the thumb's center if it were at the far right edge of the track.
        # Subtract thumb_size['width'] // 2 to get the center point of the thumb at the edge.
        # Subtract a small safety margin (e.g., 5-10 pixels) to avoid overshooting.
        absolute_max_thumb_center_x = track_location['x'] + track_size['width'] - (thumb_size['width'] // 2) - 10 # Safety margin from absolute edge

        # 1. Define a "target zone" slightly to the left of the absolute maximum.
        #    This zone ensures the slider is high, but not at the very end.
        #    The random offset (e.g., 20 to 70 pixels from the absolute_max_thumb_center_x)
        #    determines how far from the maximum it will land.
        #    Adjust these pixel values based on your slider's sensitivity and total width.
        #    A larger offset means it will be further from the maximum.
        random_offset_from_max = random.randint(25, 75) # pixels
        target_x = absolute_max_thumb_center_x - random_offset_from_max

        # 2. If the calculated target_x is too close to the start_x (or even to its left when start_x is already high),
        #    it might not register as a significant change or might try to move left when we want to move right or stay high.
        #    Ensure target_x is always to the right of start_x if start_x is not already in the "high" zone,
        #    OR ensure it's a different "high" value.
        
        # If the current position is already very high and close to our new random target,
        # force a slightly different high position.
        min_meaningful_change = 15 # pixels; minimum change to ensure UI update
        if abs(target_x - start_x) < min_meaningful_change:
            log(f"[yellow]DEBUG: Calculated target_x ({target_x}) too close to start_x ({start_x}). Adjusting.[/yellow]")
            if start_x >= absolute_max_thumb_center_x - (random_offset_from_max + min_meaningful_change):
                 target_x = start_x - min_meaningful_change
            else:
                 target_x = start_x + min_meaningful_change

        # 3. Final boundary checks:
        #    Ensure target_x doesn't go too far left (beyond the lower age thumb or start of track)
        #    and doesn't exceed our intended "near max" zone (staying away from absolute_max_thumb_center_x).
        min_thumb_x_on_track = track_location['x'] + (thumb_size['width'] // 2) + 5 # Min position on track
        target_x = max(min_thumb_x_on_track, target_x)
        
        # Ensure it doesn't go *to* the absolute max, but stays slightly before it.
        # The smallest offset from max was defined by random_offset_from_max's lower bound.
        # So, we can cap it at absolute_max_thumb_center_x minus the smallest desired offset.
        target_x = min(target_x, absolute_max_thumb_center_x - 20) # Ensure it's at least 20px from absolute max

        target_y = start_y
        # --- END OF REVISED LOGIC FOR TARGET X ---

        log(f"[yellow]DEBUG: Randomized slider movement: start_x={start_x}, target_x={target_x}, absolute_max_center_x={absolute_max_thumb_center_x}[/yellow]")

        # Ensure there is an actual move to perform
        if target_x == start_x:
            log("[yellow]DEBUG: Target_x is the same as start_x. No drag will be performed. This might mean the slider is stuck or at a boundary.[/yellow]")
            # If this happens, the Apply button might not appear.
            # You might need to handle this case, perhaps by trying a different random offset.
            # For now, we proceed, but the Apply button might fail.
        else:
            driver.execute_script('mobile: dragGesture', {
                'startX': start_x,
                'startY': start_y,
                'endX': target_x,
                'endY': target_y,
                'speed': 2500
            })
            log("[green]Higher age thumb dragged.[/green]")

        time.sleep(2) # UI update
        log("[yellow]Locating and clicking 'Apply' button...[/yellow]")
        apply_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(apply_button_locator)
        )
        apply_button.click()
        log("[green]Clicked 'Apply' button.[/green]")
        time.sleep(3) # Filters apply

        return True

    except TimeoutException:
        log(f"[red]Timeout: Could not find an element for age filter adjustment or the Apply button within {timeout}s.[/red]")
        # driver.save_screenshot("debug_timeout_age_filter.png")
        return False
    except NoSuchElementException:
        log("[red]Error: Element not found during age filter adjustment (NoSuchElementException).[/red]")
        # driver.save_screenshot("debug_noelement_age_filter.png")
        return False
    except Exception as e:
        log(f"[red]An unexpected error occurred while adjusting age filter: {e}[/red]")
        # driver.save_screenshot("debug_exception_age_filter.png")
        return False

def is_nav_bar_present(driver, timeout=3):
    """Checks if the main navigation bar is present and displayed."""
    try:
        nav_bar_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, NAV_BAR_ID))
        )
        return nav_bar_element.is_displayed() # Also check if it's actually visible
    except TimeoutException:
        return False
    except Exception as e:
        log(f"[yellow]Debug (is_nav_bar_present): Unexpected error checking nav bar: {e}[/yellow]")
        return False


def get_current_screen_by_tab(driver: webdriver.Remote, timeout=5):
    """
    Determines the current screen by checking the selected tab in the main navigation bar.
    Returns a screen identifier (e.g., "LIKED_YOU_SCREEN") or an "UNKNOWN_SCREEN..." status.
    Returns "NAV_BAR_NOT_FOUND" if the navigation bar itself is not present.
    """
    if not is_nav_bar_present(driver, timeout=max(1, timeout // 2)): # Use a portion of the main timeout
        log(f"[yellow]Debug (get_current_screen_by_tab): rain navigation bar ('{NAV_BAR_ID}') not found or not displayed.[/yellow]")
        log(f"[yellow]Backing out..[/yellow]")
        driver.back()
        if not is_nav_bar_present(driver, timeout=max(1, timeout // 2)): # Use a portion of the main timeout
            log(f"[yellow]Debug (get_current_screen_by_tab): Main navigation bar ('{NAV_BAR_ID}') not found or not displayed.[/yellow]")
            return "NAV_BAR_NOT_FOUND" # Specific return value for this case
    
    try:
        # Nav bar is confirmed present, proceed to find selected tab
        selected_tab_xpath = f"//*[@resource-id='{NAV_BAR_ID}']//android.view.ViewGroup[@selected='true' and @content-desc]"
        
        selected_tab_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.XPATH, selected_tab_xpath))
        )
        
        content_desc = selected_tab_element.get_attribute("content-desc")
        
        if content_desc:
            screen_name = content_desc.upper().replace(" ", "_") + "_SCREEN"
            return screen_name
        else:
            return "UNKNOWN_SCREEN_SELECTED_TAB_HAS_NO_CONTENT_DESC"
            
    except TimeoutException:
        # This timeout now specifically means the *selected tab* wasn't found, as nav_bar presence was checked.
        log(f"[yellow]Debug (get_current_screen_by_tab): Nav bar present, but selected tab not found within {timeout}s.[/yellow]")
        return "UNKNOWN_SCREEN_SELECTED_TAB_NOT_FOUND_IN_NAV_BAR"
    except NoSuchElementException: # Should be caught by TimeoutException
        log(f"[yellow]Debug (get_current_screen_by_tab): NoSuchElementException for selected tab.[/yellow]")
        return "UNKNOWN_SCREEN_SELECTED_TAB_NOT_FOUND_IN_NAV_BAR_NSE"
    except Exception as e:
        log(f"[red]An unexpected error occurred in get_current_screen_by_tab (after nav bar check): {e}[/red]")
        return f"UNKNOWN_SCREEN_ERROR_({type(e).__name__})"
# --- Improved open_page function ---
def open_page(driver: webdriver.Remote, page_name_from_ui, navigation_timeout=10, verification_timeout=5,logger_func: logging.Logger = rprint):
    """
    Navigates to the specified page using the bottom navigation bar if not already there.

    Args:
        driver: The Appium WebDriver instance.
        page_name_from_ui (str): The exact text from the 'content-desc' of the tab 
                                 (e.g., "Discover", "Liked You", "Chats", "Profile").
                                 This is case-sensitive.
        navigation_timeout (int): Max time to wait for tab clicking.
        verification_timeout (int): Max time to wait for screen verification after click.

    Returns:
        bool: True if successfully on the page, False otherwise.
    """
    global log
    log = logger_func
    # Standardize the target screen name for comparison with get_current_screen_by_tab
    target_screen_id = page_name_from_ui.upper().replace(" ", "_") + "_SCREEN"
    nav_bar_id = "com.bumble.app:id/mainApp_navigationTabBar"

    log(f"[yellow]Attempting to navigate to or verify '{page_name_from_ui}' (Target ID: {target_screen_id}).[/yellow]")

    # 1. Check current screen using a short timeout
    #    (get_current_screen_by_tab already has its own internal timeout)
    current_screen = get_current_screen_by_tab(driver, timeout=3) 
    log(f"[yellow]Current screen detected: {current_screen}[/yellow]")

    if current_screen == target_screen_id:
        log(f"[green]Already on the '{page_name_from_ui}' page.[/green]")
        return True
    
    # 2. If not on the target page, or if nav bar wasn't found (could be a popup)
    #    Attempt to click the target tab.
    #    The `content-desc` should match `page_name_from_ui`.
    tab_to_click_xpath = f"//*[@resource-id='{nav_bar_id}']//android.view.ViewGroup[@content-desc='{page_name_from_ui}']"

    try:
        log(f"[yellow]Not on '{page_name_from_ui}'. Attempting to click tab with content-desc: '{page_name_from_ui}'.[/yellow]")
        
        # Ensure the navigation bar itself is present first
        WebDriverWait(driver, navigation_timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, nav_bar_id))
        )
        
        # Find and click the target tab
        tab_element = WebDriverWait(driver, navigation_timeout).until(
            EC.element_to_be_clickable((AppiumBy.XPATH, tab_to_click_xpath))
        )
        tab_element.click()
        log(f"[green]Clicked on the '{page_name_from_ui}' tab.[/green]")

        # 3. Verify navigation
        #    Wait until get_current_screen_by_tab confirms we are on the target screen.
        #    This lambda function will be re-evaluated by WebDriverWait.
        WebDriverWait(driver, verification_timeout).until(
            lambda d: get_current_screen_by_tab(d, timeout=1) == target_screen_id, # Use a short timeout for each check inside lambda
            message=f"Failed to verify navigation to '{target_screen_id}' after clicking tab."
        )
        
        log(f"[green]Successfully navigated to and verified '{page_name_from_ui}' page.[/green]")
        return True

    except TimeoutException as te:
        log(f"[red]Error (open_page): TimeoutException while trying to navigate to or verify '{page_name_from_ui}'. {te.msg}[/red]")
        # For debugging, it's useful to see what screen it *thinks* it's on if verification failed
        final_check = get_current_screen_by_tab(driver, timeout=1)
        log(f"[yellow]Final screen check after TimeoutException: {final_check}[/yellow]")
        # Consider printing page source if debugging is hard:
        # if not final_check.startswith("UNKNOWN_SCREEN_NAV_BAR_OR_TAB_NOT_FOUND"):
        #     print(driver.page_source)
        return False
    except Exception as e:
        log(f"[red]Error (open_page): An unexpected error occurred while trying to open '{page_name_from_ui}'. Exception: {e}[/red]")
        # print(driver.page_source) # For debugging
        return False
