from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *
import selenium
import json
import time
from polyglot.detect import Detector
import re
import urllib.parse
from typing import *
import numpy as np
import random


class ShareGPTJSONProcessor():
    def __init__(self, json_path: str, save_path: str):
        self.json_path = json_path
        self.save_path = save_path
        self.statistics = []
        with open(self.json_path, "r") as original_json:
            self.json_dict = json.load(original_json)
        self.dialogues = self.__preprocess()

    @staticmethod
    def __split_by_sentence(value):
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', value)
        concated_sentences = []
        start = 0
        for i in range(1, len(sentences)-1):
            if sum([len(s) for s in sentences[start:i+1]]) > 1000:
                concated_sentences.append(" ".join(sentences[start:i]))
                start = i
        concated_sentences.append(" ".join(sentences[start:len(sentences)]))
        return concated_sentences, len(sentences)

    def __preprocess(self):
        """
        Preprocess JSON files to list of dialogues.
            dialogue: dict = {"id": str, "conversations": list[str], "turns": int}
                "id": unique string for identifying the dialogue.
                "conversations": list of utterances with corresponding speaker
                "turns": total number of utterances in the dialogue
        """
        with open(self.json_path, "r") as original_json:
            dict_list = json.load(original_json)
            for entry in dict_list:
                # must have at least 2 elements: "id", "conversations"
                if len(entry) < 2:
                    continue
                original_convs = entry["conversations"]
                if original_convs is None:
                    continue
                conversations = []
                human_languages = []
                sentence_nums = []
                lengths = []
                speakers = []
                turns = len(original_convs)
                for i in range(0, turns):
                    # to decide one language per id
                    if original_convs[i]["from"] == "human":
                        language = Detector(original_convs[i]["value"], quiet=True).language.code
                        human_languages.append(language)

                    # for statistics - to know lengths of each utterance
                    lengths.append(len(original_convs[i]["value"]))
                    
                    sentences, sent_num = self.__split_by_sentence(original_convs[i]["value"])
                    sentence_nums.append(sent_num)
                    for j in range(0, len(sentences)):
                        speaker = original_convs[i]["from"] + str(i) + "_" + str(j)
                        speakers.append(speaker)
                        conversations.append("\"" + speaker + "\"" + ":" + sentences[j])

                # update entry
                entry["conversations"] = conversations
                entry["speakers"] = speakers
                entry["language"] = max(set(human_languages), key = human_languages.count)
                if entry["language"] == "un":
                    entry["language"] = "auto"

                # record statistics
                self.statistics.append({"id": entry["id"], "lengths": lengths, "sentence_nums": sentence_nums, "turns": turns})
        return dict_list

    def view_statistics(self):
        lengths = [l for d in self.statistics for l in d["lengths"]]
        tot_lengths = [sum(d["lengths"]) + len(d["lengths"]) - 1 for d in self.statistics]
        sentence_nums = [l for d in self.statistics for l in d["sentence_nums"]]
        turns = [d["turns"] for d in self.statistics]
        l_statistics = [np.min(lengths), np.max(lengths), np.mean(lengths), np.std(lengths)]
        tl_statistics = [np.min(tot_lengths), np.max(tot_lengths), np.mean(tot_lengths), np.std(tot_lengths)]
        s_statistics = [np.min(sentence_nums), np.max(sentence_nums), np.mean(sentence_nums), np.std(sentence_nums)]
        t_statistics = [np.min(turns), np.max(turns), np.mean(turns), np.std(turns)]
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["", "min", "max", "mean", "std"]))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["len"]+l_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["tot_len"]+tl_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["sent_num"]+s_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["turns"]+t_statistics))
    
    def save_translations_as_json(self, translations):
        assert len(translations) == len(self.save_path)
        for i in range(0, len(self.save_path)):
            with open(self.save_path[i], "w") as json_file:
                json.dump(translations[i], json_file)
        

    
class ProxyServerRetriever():
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
                except (WebDriverException, TimeoutException):
                    driver.quit()
        return None


class GoogleTranslateAgent():
    def __init__(self, driver, timeout=600, max_len=(5000, 16300), overlap=(1000, 3000)):
        self.driver = driver
        self.timeout = timeout
        self.max_len = max_len
        self.overlap = overlap

    @staticmethod
    def __generate_url(lang_from, lang_to, text):
        text = urllib.parse.quote(text)
        url = "https://translate.google.co.in/?sl="+lang_from+"&tl="+lang_to+"&text="+text+"&op=translate"
        return url

    @staticmethod
    def __translation_length(dialogue):
        return sum(len(utternace) for utternace in dialogue) + len(dialogue) - 1
    
    @staticmethod
    def __url_length(dialogue): #16300
        return sum(len(urllib.parse.quote(utterance)) for utterance in dialogue) + 3*len(dialogue) - 1

    def __is_length_ok(self, dialogue, max_len = None):
        if max_len is None:
            max_len = self.max_len
        txt_len_ok = self.__translation_length(dialogue) < max_len[0]
        url_len_ok = self.__url_length(dialogue) < max_len[1]
        return txt_len_ok and url_len_ok
    
    def get_tranlation_response_timeout(self, lang_from, lang_to, text):
        time_passed = 0
        self.driver.get(self.__generate_url(lang_from, lang_to, text))
        while True:
            try:
                output = self.driver.find_element(By.CLASS_NAME,'HwtZe').text
                time.sleep(random.randrange(1,6))
                break
            except:
                if time_passed > self.timeout:
                    return (-1, "[ERROR] Max time (" + str(time) + " secs) has elapsed")
                time.sleep(1)
                time_passed += 1
                pass
        return (0, output)

    def split_text_with_overlap(self, dialogue):
        start_index = 0
        next_start_index = 0
        splitted_dialogue = []
        splitting_index = []
        for i in range(1, len(dialogue)):
            if next_start_index <= start_index \
                and not self.__is_length_ok(dialogue[start_index:i+1], np.array(self.max_len)-np.array(self.overlap)):
                next_start_index = i
            if not self.__is_length_ok(dialogue[start_index:i+1]):
                print(self.__url_length(dialogue[start_index:i]), self.__translation_length(dialogue[start_index:i]))
                splitted_dialogue.append("\n".join(dialogue[start_index:i]))
                splitting_index.append((start_index, i))
                start_index = next_start_index
        splitted_dialogue.append("\n".join(dialogue[start_index:len(dialogue)]))
        splitting_index.append((start_index, len(dialogue)))
        print(self.__url_length(dialogue[start_index:len(dialogue)]), self.__translation_length(dialogue[start_index:len(dialogue)]))
        return splitted_dialogue, splitting_index

    def __merge_splitted_translation(splitted_result, splitting_index, speakers):
        merged = splitted_result[0]
        for i in range(0, len(splitted_result) - 1):
            start_index = re.search('"?'+speakers[splitting_index[i][1]]+'"?:\s?', splitted_result[i+1].lower())
            if start_index is None:
                print(i)
                print(speakers[splitting_index[i][1]])
                print(splitted_result[i+1])
            else:
                start_index = start_index.start()
            merged += '\n' + splitted_result[i+1][start_index:]
        return merged

    def __translate_helper(self, lang_from, lang_to, dialogue, speakers):
        if self.__is_length_ok(dialogue):
            # no need to split the text
            text = "\n".join(dialogue)
            state, result = self.get_tranlation_response_timeout(lang_from, lang_to, text)
            if state == -1:
                raise Exception(result) #이게 뭔
            else: # translated !
                return result
        else:
            splitted_dialogue, splitting_index = self.split_text_with_overlap(dialogue)
            print(splitting_index)
            states_and_results = list(map(lambda x: self.get_tranlation_response_timeout(lang_from, lang_to, x), splitted_dialogue))
            states, results = list(zip(*states_and_results))
            if -1 in states:
                raise Exception("Timeout Occured") # ...
            else:
                return self.__merge_splitted_translation(results, splitting_index, speakers)

    @staticmethod
    def __convert_translation_to_save_format(translation, speakers):
        convs = [] 
        start_index = re.search('"?'+speakers[0]+'"?:\s?', translation.lower())
        for i in range(0, len(speakers)):
            speaker = speakers[i]
            next_start_index = re.search('"?'+speakers[i+1]+'"?:\s?', translation.lower())
            speaker = re.sub(r'[^a-zA-Z]', '', speaker)
            if convs[-1]["from"] == speaker:
                convs[-1]["value"] += " " + translation[start_index.end():next_start_index.start()-1]
            else:
                utterance = {}
                utterance["from"] = speaker
                utterance["value"] = translation[start_index.end():next_start_index.start()-1] # exclued manually added newline character
                convs.append(utterance)
            start_index = next_start_index
        return convs

    def translate(self, lang_from, lang_to, dialogue, speakers):
        result = self.__translate_helper(lang_from, lang_to, dialogue, speakers)
        formatted_result = self.__convert_translation_to_save_format(result)
        return formatted_result