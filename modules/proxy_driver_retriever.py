from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By

class ProxyDriverRetriever():
    def __init__(self, driver_path):
        self.driver_path = driver_path
        self.driver = webdriver.Chrome(driver_path)
    
    def __get_free_proxy(self, n):
        self.driver.get("https://free-proxy-list.net/")
        tr_list = self.driver.find_element(By.CLASS_NAME, 'fpl-list').find_elements(By.TAG_NAME, "tr")[1:]
        top_n = list(map(lambda x: x.find_elements(By.TAG_NAME, "td"), tr_list[0:n]))
        top_n = list(map(lambda x: x[0].text + ":" + x[1].text, top_n))
        return top_n

    def set_proxy_server(self, trial=3, n=50):
        for i in range(0, trial):
            proxy_list = self.__get_free_proxy(n)
            for proxy in proxy_list:
                webdriver.DesiredCapabilities.CHROME['proxy'] = {
                    "httpProxy": proxy,
                    "ftpProxy": proxy,
                    "sslProxy": proxy,
                    "proxyType": "MANUAL"
                }
                driver = webdriver.Chrome(self.driver_path)
                try:
                    if len(driver.find_elements(By.CSS_SELECTOR,'.error-code')) > 0:
                        driver.quit()
                        continue
                    return driver 
                except:
                    driver.quit()
        return None