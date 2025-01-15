import time
import datetime
import locale
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import argparse

class BookingScraper:
    def __init__(self):    
        self.driver = webdriver.Chrome()   
        self.collected_data = pd.DataFrame(columns=['Content', 'Country', 'Score', 'Positive', 'Negative', 'Date'])

    def collect_data(self):
        data = []
        
        elements = self.driver.find_elements(By.XPATH, '//div[@data-testid="review-card"]')
        for element in elements:          
            try:
                text_review = element.find_element(By.XPATH, './/div[@data-testid="review-title"]').text
            except:
                text_review = None
            try:
                country = element.find_element(By.XPATH, './/div[@data-testid="review-avatar"]//img/following-sibling::span[1]').text
            except:
                country = None
            try:
                score = element.find_element(By.XPATH, './/div[@data-testid="review-score"]/div/div/div').text
                # score = score.split(' ')[-1]
                # score = int(score.split(',')[0]) 
            except:
                score = None
            try:
                positive_text = element.find_elements(By.XPATH, './/div[@data-testid="review-positive-text"]//span')[1].text
            except:
                positive_text = None
            try:
                negative_text = element.find_elements(By.XPATH, './/div[@data-testid="review-negative-text"]//span')[1].text
            except:
                negative_text = None
            try:
                date = element.find_element(By.XPATH, './/span[@data-testid="review-date"]').text
                # date = self.extract_date_from_string(date)
            except:
                date = None
        
            data.append({
                'Content': text_review,
                'Country': country,
                'Score': score,
                'Positive': positive_text,
                'Negative': negative_text,
                'Date': date
            })

        self.collected_data = pd.concat([self.collected_data, pd.DataFrame(data)], ignore_index=True)

    @staticmethod
    def extract_date_from_string(date_string):
        current_locale = locale.getlocale(locale.LC_TIME)
        
        try:
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        except locale.Error:
            print("Locale française non disponible sur ce système.")
            return None

        date_part = date_string.replace("Commentaire envoyé le", "").strip()
        date_format = "%d %B %Y"
        
        try:
            date_object = datetime.datetime.strptime(date_part, date_format)
        except ValueError as e:
            print(f"Erreur de formatage de la date: {e}")
            date_object = None
        finally:
            locale.setlocale(locale.LC_TIME, current_locale)

        return date_object

    def go_to_next_page(self):
        try:
            next_button = self.driver.find_element(By.XPATH, '//button[@aria-label="Page suivante"][contains(@class,"bb803d8689")]')
            next_button.click()
            time.sleep(1)
            return True
        except Exception as e:
            print("Impossible de trouver le bouton 'Suivant' : ", str(e))
            return False

    def run(self, url=None):
        print(f"Processing collection : {url}")
        self.driver.get(url)
        time.sleep(2)

        while True:
            self.collect_data()
            self.collected_data.to_excel("reviews_data.xlsx", index=False)
            if not self.go_to_next_page():
                print("Fin du scraping, dernière page atteinte.")
                break
        
        save_path = "hotel_reviews_trianon_rive_gauche.xlsx"
        self.collected_data.to_excel(save_path, index=False)
        print(f"Scraping terminé. Fichier {save_path} sauvegardé.")

def main():
    parser = argparse.ArgumentParser(description="Booking Scraper")
    parser.add_argument('--url', type=str, help='Specific URL to scrape')
    args = parser.parse_args()

    scraper = BookingScraper()
    scraper.run(url=args.url)
    scraper.driver.quit()

if __name__ == "__main__":
    main()
