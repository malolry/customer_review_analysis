import csv
import logging
import os
import random
import re
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Configuration
REVIEW_URL = "https://www.tripadvisor.fr/Hotel_Review-g187147-d228737-Reviews-Hotel_Trianon_Rive_Gauche-Paris_Ile_de_France.html"
OUTPUT_FILE = "hotel_trianon_reviews.csv"
LOG_FILE = "scraper.log"
HEADLESS = False  # Set to True to run in headless mode
MAX_PAGES = 305  # Set to a high number or remove to scrape all pages

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger("TripAdvisorScraper")

def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """Initializes and returns a Selenium WebDriver with desired options."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        logger.info("WebDriver initialized successfully.")
        return driver
    except WebDriverException as e:
        logger.error(f"Error initializing WebDriver: {e}")
        sys.exit(1)

def handle_cookies(driver: webdriver.Chrome):
    """Rejects all cookies if the cookie banner is present."""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "onetrust-banner-sdk"))
        )
        logger.info("Cookie banner detected. Attempting to reject all cookies.")

        reject_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
        )
        reject_button.click()
        logger.info("'Reject All' button clicked on cookie banner.")

        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "onetrust-banner-sdk"))
        )
        logger.info("Cookie banner successfully handled.")

        random_sleep(2, 4)

        # Attempt to close any additional modal
        try:
            close_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button[data-automation='closeModal']")
                )
            )
            close_button.click()
            logger.info("Additional modal detected and closed.")
        except TimeoutException:
            logger.info("No additional modal detected after rejecting cookies.")
        except Exception as e:
            logger.error(f"Error while trying to close additional modal: {e}")

    except TimeoutException:
        logger.info("No cookie banner detected.")
    except Exception as e:
        logger.error(f"Error handling cookie banner: {e}")

def detect_captcha(driver: webdriver.Chrome) -> bool:
    """Detects if a CAPTCHA is present on the current page."""
    try:
        captcha_iframes = driver.find_elements(
            By.XPATH, "//iframe[contains(@src, 'captcha') or contains(@src, 'recaptcha')]"
        )
        captcha_messages = driver.find_elements(
            By.XPATH, "//div[contains(text(), 'Please verify you are a human')]"
        )
        if captcha_iframes or captcha_messages:
            logger.warning("CAPTCHA detected!")
            return True
        return False
    except Exception as e:
        logger.error(f"Error in CAPTCHA detection: {e}")
        return False

def random_sleep(min_seconds: float = 2, max_seconds: float = 4):
    """Sleeps for a random duration to mimic human behavior."""
    duration = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sleeping for {duration:.2f} seconds.")
    time.sleep(duration)

def initialize_csv(file_path: str, headers: list):
    """Initializes a CSV file with headers if it doesn't exist."""
    if not os.path.exists(file_path):
        try:
            with open(file_path, "w", newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(headers)
            logger.info(f"Initialized {file_path} with headers.")
        except Exception as e:
            logger.error(f"Error initializing {file_path}: {e}")

def extract_reviews(driver: webdriver.Chrome) -> list:
    """Extracts reviews from the current page."""
    reviews = []
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[@data-test-target="HR_CC_CARD"]'))
        )
        review_cards = driver.find_elements(By.XPATH,'//div[@data-test-target="reviews-tab"]//div[@data-test-target="HR_CC_CARD"]')
        logger.info(f"Found {len(review_cards)} reviews on the current page.")

        for review in review_cards:
            try:
                # Extract review text
                body_element = review.find_element(
                    By.XPATH,
                    './/div[@data-reviewid]//div//div//div//span//span'
                )
                body = body_element.text.strip().replace("\n", " ").replace("\r", " ").replace(";", ",")

                # Extract rating
                rating_element = review.find_element(
                    By.XPATH,
                    ".//div[@data-test-target]//*[local-name()='svg']/*[local-name()='title'][contains(., 'bulles')]"
                )
                rating_text = rating_element.text
                rating_match = re.search(r'(\d+(\,\d+)?) sur', rating_text)   
                rating = float(rating_match.group(1).replace(",", ".")) if rating_match else None

                reviews.append((body, rating))
            except NoSuchElementException:
                logger.debug("A review element was missing expected fields. Skipping.")
                continue
            except Exception as e:
                logger.error(f"Error extracting a review: {e}")
                continue

    except TimeoutException:
        logger.error("Timeout while waiting for reviews to load.")
    except Exception as e:
        logger.error(f"Error extracting reviews: {e}")

    return reviews

def save_reviews(file_path: str, reviews: list):
    """Saves reviews to a CSV file."""
    if not reviews:
        return
    try:
        with open(file_path, "a", newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(reviews)
        logger.info(f"Saved {len(reviews)} reviews to {file_path}.")
    except Exception as e:
        logger.error(f"Failed to write reviews to file: {e}")

def navigate_and_scrape(driver: webdriver.Chrome, output_file: str, max_pages: int = 50):
    """Navigates through all review pages and scrapes reviews."""
    try:
        driver.get(REVIEW_URL)
        logger.info(f"Navigated to {REVIEW_URL}")
        random_sleep()

        handle_cookies(driver)

        if detect_captcha(driver):
            logger.warning("CAPTCHA detected. Please solve it manually in the browser.")
            input("After solving the CAPTCHA in the browser, press Enter to continue...")
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            if detect_captcha(driver):
                logger.error("CAPTCHA still detected after manual intervention. Exiting.")
                sys.exit(1)

        current_page = 1
        while current_page <= max_pages:
            logger.info(f"Processing reviews page {current_page}.")
            reviews = extract_reviews(driver)
            save_reviews(output_file, reviews)

            # Check for next page
            try:
                next_button = driver.find_element(By.XPATH, "//a[@aria-label='Page suivante']")
                if 'disabled' in next_button.get_attribute('class'):
                    logger.info("No more review pages available.")
                    break
                next_button.click()
                logger.info(f"Navigated to page {current_page + 1}.")
                current_page += 1
                random_sleep()
            except NoSuchElementException:
                logger.info("Next button not found. Reached the last page.")
                break
            except Exception as e:
                logger.error(f"Error navigating to the next page: {e}")
                break

    except Exception as e:
        logger.error(f"An error occurred during navigation and scraping: {e}")
    finally:
        driver.quit()
        logger.info("WebDriver closed.")

def main():
    # Initialize CSV with headers
    initialize_csv(OUTPUT_FILE, ["Review", "Rating"])

    # Setup WebDriver
    driver = setup_driver(headless=HEADLESS)

    # Start scraping
    navigate_and_scrape(driver, OUTPUT_FILE, max_pages=MAX_PAGES)

if __name__ == "__main__":
    main()
