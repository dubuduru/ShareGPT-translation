from selenium import webdriver
from helper import *

DRIVER_PATH = "./chromedriver_mac_arm64/chromedriver"
LANG_FROM = "auto" # "en" available
LANG_TO = "ko"
JSON_PATH = [
    "./data/sg_90k_part1_html_cleaned.json",
    "./data/sg_90k_part2_html_cleaned.json"
]
SAVE_PATH = [
    "./data/sg_90k_part1_html_cleaned_ko.json",
    "./data/sg_90k_part2_html_cleaned_ko.json"
]


FILE_NUM = 2

Driver = webdriver.Chrome(DRIVER_PATH)
Translator = GoogleTranslateAgent(Driver)
for i in range(0, FILE_NUM):
    json_processor = ShareGPTJSONProcessor(JSON_PATH[i], SAVE_PATH[i])
    translations = []
    for d in json_processor.dialogues:
        result = Translator.translate(d["language"], LANG_TO, d["conversations"], d["speakers"])
        translations.append({"id": d["id"], "conversations": result})
        print(translations[-1])

