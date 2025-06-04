import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from helper import open_page
from swipe import realistic_swipe
import chat

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
driver = None

try:
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)

    time.sleep(5)
    print("THE APP IS READY")


    # if open_page(driver, "People"):
    #     realistic_swipe(driver,1)
    print("\n--- Attempting Chat Processing Phase ---")
    if open_page(driver, "Chats"): # Ensure "Chats" is the exact content-desc
        print("Successfully navigated to Chats page.")
        # Now call the function from your chat.py module
        # If you imported the whole module: chat.process_new_matches(...)
        # If you imported specific function: process_new_matches(...)
        chat.process_new_matches(driver, max_matches_to_process=3) # Process up to 3 new matches
        print("Finished chat processing phase.")

except Exception as e:
    print(f"Error: {e}")
finally:
    if driver:
        driver.quit()
