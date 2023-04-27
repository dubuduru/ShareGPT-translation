from typing import *
import time
import random
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *


class GoogleTranslateAgent():

    def __init__(self, driver, timeout: int = 600, max_len: Tuple[int, int] = (5000, 16300)):
        self.driver = driver
        self.timeout = timeout
        self.max_len = max_len

    
    def is_length_ok(self, text: str):
        txt_len_ok = len(text) <= self.max_len[0]
        url_len_ok = len(urllib.parse.quote(text)) <= self.max_len[1]
        return txt_len_ok and url_len_ok

    
    @staticmethod
    def __generate_url(lang_from: str, lang_to: str, text: str):
        text = urllib.parse.quote(text)
        url = "https://translate.google.co.in/?sl="+lang_from+"&tl="+lang_to+"&text="+text+"&op=translate"
        return url
    
    
    def get_translation(self, lang_from: str, lang_to: str, text: str):
        if not self.is_length_ok(text):
            return (-1, "[ERROR] Translator: Given text exceeded maximum length")
        
        time_passed = 0
        url = self.__generate_url(lang_from, lang_to, text)
        self.driver.get(url)
        
        while True:
            try:
                is_error = (len(self.driver.find_elements(By.CLASS_NAME,'Jj6Lae')) > 0)
                if is_error:
                    self.driver.get(url)
                    time.sleep(1)
                    time_passed += 1
                    continue
                output = self.driver.find_element(By.CLASS_NAME,'HwtZe').text
                time.sleep(random.randrange(1,6))
                break
            
            except:
                if time_passed > self.timeout:
                    return (-1, "[ERROR] Translator: Timeout occured (" + str(self.timeout) + " secs elapsed)")
                time.sleep(1)
                time_passed += 1
                pass
        
        return (0, output)

    
    def change_driver_to(self, new_driver):
        self.driver.quit()
        self.driver = new_driver