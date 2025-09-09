import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

MAGENTO = "https://magento.softwaretestingboard.com/"

@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")            # headless mode
    options.add_argument("--window-size=1920,1080")   # required for headless rendering
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    yield driver
    driver.quit()

def safe_click(driver, by, value, retries=3, delay=2):
    """Retries clicking element to avoid stale or timing issues."""
    for attempt in range(retries):
        try:
            elem = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((by, value))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
            elem.click()
            return
        except (TimeoutException, StaleElementReferenceException):
            time.sleep(delay)
    raise Exception(f"Could not click element: {value}")

def safe_send_keys(driver, by, value, keys, retries=3, delay=2):
    """Retries sending keys to element to avoid stale issues."""
    for attempt in range(retries):
        try:
            elem = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((by, value))
            )
            elem.clear()
            elem.send_keys(keys)
            return
        except (TimeoutException, StaleElementReferenceException):
            time.sleep(delay)
    raise Exception(f"Could not send keys to element: {value}")

def test_payment_gateway_redirection(driver):
    wait = WebDriverWait(driver, 90)  # long wait for slow pages

    # Step 1: Open Magento site
    driver.get(MAGENTO)
    time.sleep(5)  # give JS a moment to render

    # Step 2: Wait for product container
    product_container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.products.wrapper.grid.products-grid"))
    )

    products = product_container.find_elements(By.CSS_SELECTOR, "a.product-item-link")
    assert products, "No products found"
    safe_click(driver, By.CSS_SELECTOR, "a.product-item-link")  # click first product

    # Step 3: Add to cart
    safe_click(driver, By.ID, "product-addtocart-button")

    # Step 4: Wait for success message
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.message-success")))

    # Step 5: Open mini cart & proceed to checkout
    safe_click(driver, By.CSS_SELECTOR, "a.action.showcart")
    safe_click(driver, By.ID, "top-cart-btn-checkout")

    # Step 6: Fill shipping info
    safe_send_keys(driver, By.NAME, "firstname", "John")
    safe_send_keys(driver, By.NAME, "lastname", "Doe")
    safe_send_keys(driver, By.NAME, "street[0]", "123 Test St")
    safe_send_keys(driver, By.NAME, "city", "New York")
    safe_send_keys(driver, By.NAME, "postcode", "10001")
    safe_send_keys(driver, By.NAME, "telephone", "9876543210")
    Select(driver.find_element(By.NAME, "country_id")).select_by_visible_text("United States")
    Select(driver.find_element(By.NAME, "region_id")).select_by_visible_text("New York")

    safe_click(driver, By.XPATH, "//button[@data-role='opc-continue']")  # continue

    # Step 7: Wait for payment methods
    wait.until(EC.visibility_of_element_located((By.ID, "checkout-payment-method-load")))
    payment_methods = driver.find_elements(By.XPATH, "//div[@id='checkout-payment-method-load']//input[@type='radio']")
    assert payment_methods, "No payment methods found"
    driver.execute_script("arguments[0].click();", payment_methods[0])

    # Step 8: Place order
    place_order_btn = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@title='Place Order']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", place_order_btn)
    place_order_btn.click()

    # Step 9: Verify success
    success_msg = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "div.checkout-success"))
    )
    assert "Thank you" in success_msg.text
    print("✅ Order placed successfully in headless mode with retries")
