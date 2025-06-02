import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

options = UiAutomator2Options()
options.platform_name = "Android"
options.platform_version = "12"
options.device_name = "128.14.109.187:21384"
options.automation_name = "UiAutomator2"
options.app_package = "com.bumble.app"
# options.app_activity = "com.bumble.app.ui.screenstories.ScreenStoryBlockersActivity"
options.no_reset = True
options.uiautomator2_server_install_timeout = 120000

APPIUM_SERVER_URL = "http://127.0.0.1:4723"
driver = None

try:
    driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
    print("opened the app")

    resource_id_for_button_7 = 'new UiSelector().className("android.widget.Button").instance(4)'
    
    button_7 = driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, resource_id_for_button_7 )

    time.sleep(3)

except Exception as e:
    print(f"Error: {e}")
finally:
    if driver:
        driver.quit()
