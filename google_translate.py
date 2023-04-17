from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
import selenium
import json
import time


DRIVER_PATH = "./chromedriver_mac_arm64/chromedriver"
LANG_FROM = "auto" # "en" available
LANG_TO = "ko"
JSON_PATH = [
    "./data/sg_90k_part1_html_cleaned.json",
    "./data/sg_90k_part2_html_cleaned.json"
]

# 데이터 통계 (길이 분포, turn num, 언어 분포 ?, etc ..)
# polyglot -> 처리할 때 통계 (얼마나 드랍되는지)
# fastchat code 참고
def preprocess_with_utterance_index(json_path):
    with open(json_path, "r") as original_json:
        json_list = json.load(original_json)
        for entry in json_list:
            # must have at least 2 elements: "id", "conversation"
            if len(entry) < 2:
                continue
            original_convs = entry["conversations"]
            if original_convs is None:
                continue
            # concat_convs = ""
            # # concatenate 
            # for i in range(0, len(original_convs)):
            #     concat_convs += original_convs[i]["from"] + str(i) + ":" + original_convs[i]["value"].replace("\n", "%0A") + "%0A"
            # # delete the last new line character
            # concat_convs = concat_convs[:-3]
            concat_convs = []
            for i in range(0, len(original_convs)):
                concat_convs += ["\"" + original_convs[i]["from"]  + str(i) + "\"" + ":" + original_convs[i]["value"].replace("\n", "%0A")]
            entry["conversations"] = concat_convs
            entry["turns"] = len(original_convs)
    return json_list


def get_free_proxy(driver, n):
    driver.get("https://free-proxy-list.net/")
    tr_list = driver.find_element(By.CLASS_NAME, 'fpl-list').find_elements(By.TAG_NAME, "tr")[1:]
    top_n = list(map(lambda x: x.find_elements(By.TAG_NAME, "td"), tr_list[0:n]))
    top_n = list(map(lambda x: x[0].text + ":" + x[1].text, top_n))
    return top_n

def set_proxy_server(proxy_retrieving_driver, trial=3, n=50):
    for i in range(0, trial):
        proxy_list = get_free_proxy(proxy_retrieving_driver, n)
        for proxy in proxy_list:
            webdriver.DesiredCapabilities.CHROME['proxy'] = {
                "httpProxy": proxy,
                "ftpProxy": proxy,
                "sslProxy": proxy,
                "proxyType": "MANUAL"
            }
            driver = webdriver.Chrome(DRIVER_PATH)
            try:
                driver.get("https://translate.google.co.in/")
                return driver
            except (WebDriverException, TimeoutException):
                driver.quit()
    return None
    
    
def get_tranlation_response_timeout(driver, lang_from, lang_to, text, timeout):
    time_passed = 0
    driver.get("https://translate.google.co.in/?sl="+lang_from+"&tl="+lang_to+"&text="+text+"&op=translate")
    while True:
        try:
            output = driver.find_element(By.CLASS_NAME,'HwtZe').text
            break
        except:
            if time_passed > timeout:
                return (-1, "[ERROR] Max time (" + str(time) + " secs) has elapsed")
            time.sleep(1)
            time_passed += 1
            pass
    return (0, output)


def translation_length(dialogue):
    return sum(len(s) for s in dialogue) + len(dialogue) - 1


def split_text_with_overlap(dialogue, max_len, overlap):
    start_index = 0
    next_start_index = 0
    splitted_dialogue = []
    splitting_index = []
    for i in range(0, len(dialogue)):
        if next_start_index <= start_index and translation_length(dialogue[start_index:i]) > (max_len - overlap):
            next_start_index = i-1
        if translation_length(dialogue[start_index:i]) > max_len:
            splitted_dialogue.append("%0A".join(dialogue[start_index:i-1]))
            splitting_index.append((start_index, i-1))
            start_index = next_start_index
    splitted_dialogue.append("%0A".join(dialogue[next_start_index:len(dialogue)]))
    splitting_index.append((start_index, len(dialogue)))
    return splitted_dialogue, splitting_index


def split_text_with_overlap_v2(dialogue, max_len, overlap):
    if overlap > max_len:
        overlap = int(max_len / 2)
    start_index = 0
    next_start_index = 0
    splitted_dialogue = []
    splitting_index = []
    for i in range(0, len(dialogue)):
        if translation_length(dialogue[start_index:i]) > max_len:
            splitted_dialogue.append("%0A".join(dialogue[start_index:i-1]))
            splitting_index.append((start_index, i-1))
            for j in reversed(range(start_index, i-1)):
                if translation_length(dialogue[j:i-1]) > overlap:
                    next_start_index = j
                    break
            if next_start_index <= start_index:
                # sth went wrong - go on with no overlap
                next_start_index = i-1
            start_index = next_start_index
    splitted_dialogue.append("%0A".join(dialogue[next_start_index:len(dialogue)]))
    splitting_index.append((start_index, len(dialogue)))
    return splitted_dialogue, splitting_index


def speaker_with_utterance_index(index):
    if index%2 == 0:
        return "human" + str(index)
    else:
        return "gpt" + str(index)


def merge_splitted_translation(splitted_result, splitting_index):
    merged = splitted_result[0]
    for i in range(0, len(splitted_result) - 1):
        start_index = splitted_result[i+1].lower.find(speaker_with_utterance_index(splitting_index[i][1]))
        merged += '\n' + splitted_result[i+1][start_index:]
    return merged


def translate(driver, lang_from, lang_to, dialogue, timeout=600, max_len=5000):
    if translation_length(dialogue) < max_len:
        # no need to split the text
        text = "%0A".join(dialogue)
        state, result = get_tranlation_response_timeout(driver, lang_from, lang_to, text, timeout)
        if state == -1:
            raise Exception(result) #이게 뭔
        else: # translated !
            return result
    else:
        splitted_dialogue, splitting_index = split_text_with_overlap(dialogue, max_len, overlap = 2500)
        states_and_results = list(map(lambda x: get_tranlation_response_timeout(driver, lang_from, lang_to, x, timeout), splitted_dialogue))
        states, results = list(zip(*states_and_results))
        if -1 in state:
            raise Exception(result) # ...
        else:
            return merge_splitted_translation(results, splitting_index)


def convert_translation_to_save_format(translation, turns):
    convs = []
    start_index = translation.lower.find(speaker_with_utterance_index(0))
    for i in range(0, turns-1):
        speaker = speaker_with_utterance_index(i)
        next_start_index = translation.lower.find(speaker_with_utterance_index(i+1))
        utterance = {}
        utterance["from"] = speaker[:-1]
        utterance["value"] = translation[start_index+len(speaker)+1:next_start_index-1] # exclued manually added newline character
        convs += utterance
        start_index = next_start_index
    return convs
            


if __name__ == "__main__":
    proxy_retrieving_driver = webdriver.Chrome(DRIVER_PATH)
    driver = set_proxy_server(proxy_retrieving_driver)
    if driver is None:
        driver = proxy_retrieving_driver # giving up setting proxy driver
    for path in JSON_PATH:
        json_save = []
        preprocessed_list = preprocess_with_utterance_index(path)
        for dialogue in preprocessed_list:
            translation = translate(driver, "auto", "ko", dialogue["conversations"])
            dict_converted = convert_translation_to_save_format(translation, dialogue["turns"])
            json_entry = {"id": dialogue["id"], "conversations": dict_converted}
            json_save.append(json_entry)
        with open("KO_" + JSON_PATH, "w") as json_file:
            json.dump(json_save, json_file)