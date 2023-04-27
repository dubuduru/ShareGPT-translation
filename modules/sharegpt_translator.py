
from typing import *
import re
import urllib.parse
import numpy as np
from selenium import webdriver
from .google_translate_agent import GoogleTranslateAgent
from .log_printer import *

from configs.sg_config import DRIVER_PATH


class ShareGPTTranslator():
    
    def __init__(self, default_lang, include_errs: bool = False, timeout: int = 600, max_len: Tuple[int, int] = (5000, 16300), overlap: Tuple[int, int] = (1000, 3000)):
        self.__translator = GoogleTranslateAgent(webdriver.Chrome(DRIVER_PATH), timeout, max_len)
        self.__include_errs = include_errs
        self.__max_len = max_len
        self.__overlap = overlap

        self.default_lang = default_lang

    
    def change_driver_to(self, new_driver):
        self.__translator.change_driver_to(new_driver)
   

    @staticmethod
    def __translation_length(dialogue: list[str]):
        return sum(len(utternace) for utternace in dialogue) + len(dialogue) - 1
    
    
    @staticmethod
    def __url_length(dialogue: list[str]): #16300
        return sum(len(urllib.parse.quote(utterance)) for utterance in dialogue) + 3*len(dialogue) - 1

    
    def __is_length_ok(self, dialogue: list[str], max_len: Tuple[int, int] = None):
        if max_len is None:
            max_len = self.__max_len
        txt_len_ok = self.__translation_length(dialogue) < max_len[0]
        url_len_ok = self.__url_length(dialogue) < max_len[1]
        return txt_len_ok and url_len_ok

    
    def __split_text_with_context(self, dialogue: list[str]):
        start_index = 0
        next_start_index = 0
        split_dialogue = []
        split_index = []
        for i in range(1, len(dialogue)):
            if next_start_index <= start_index \
                and not self.__is_length_ok(dialogue[start_index:i+1], np.array(self.__max_len)-np.array(self.__overlap)):
                next_start_index = i
            if not self.__is_length_ok(dialogue[start_index:i+1]):
                split_dialogue.append("\n".join(dialogue[start_index:i]))
                split_index.append((start_index, i))
                start_index = next_start_index
        split_dialogue.append("\n".join(dialogue[start_index:len(dialogue)]))
        split_index.append((start_index, len(dialogue)))
        return split_dialogue, split_index

    
    @staticmethod
    def __merge_translations(splitted_result: list[str], splitting_index: list[Tuple[int, int]], speakers: list[str]):
        merged = splitted_result[0]
        for i in range(0, len(splitted_result) - 1):
            start_index = re.search('"?'+speakers[splitting_index[i][1]]+'"?:\s?', splitted_result[i+1].lower())
            if start_index is None:
                return (2, splitted_result)
            else:
                start_index = start_index.start()
            merged += '\n' + splitted_result[i+1][start_index:]
        return (0, merged)


    @staticmethod
    def __split_translation_into_utterances(translation, speakers, turns):
        convs = [] 
        start_index = re.search('"?'+speakers[0]+'"?:\s?', translation.lower())
        if start_index is None:
            return (3, translation)
        for i in range(0, len(speakers)-1):
            speaker = speakers[i]
            next_start_index = re.search('"?'+speakers[i+1]+'"?:\s?', translation.lower())
            if next_start_index is None:
                return (3, translation)
            speaker = re.sub(r'[^a-zA-Z]', '', speaker)
            if len(convs) > 0 and convs[-1]["from"] == speaker:
                convs[-1]["value"] += " " + translation[start_index.end():next_start_index.start()-1]
            else:
                utterance = {}
                utterance["from"] = speaker
                utterance["value"] = translation[start_index.end():next_start_index.start()-1] # exclued manually added newline character
                convs.append(utterance)
            start_index = next_start_index
        speaker = speakers[len(speakers)-1]
        speaker = re.sub(r'[^a-zA-Z]', '', speaker)
        if len(convs) > 0 and convs[-1]["from"] == speaker:
            convs[-1]["value"] += " " + translation[start_index.end():]
        else:
            utterance = {}
            utterance["from"] = speaker
            utterance["value"] = translation[start_index.end():] # exclued manually added newline character
            convs.append(utterance)
        
        if len(convs) != turns:
            return (4, convs)
        else:
            return (0, convs)  
    
    
    def __translate_with_context(self, lang_from, lang_to, dialogue, speakers, turns):
        if self.__is_length_ok(dialogue):
            # no need to split the text
            text = "\n".join(dialogue)
            state, result = self.__translator.get_translation(lang_from, lang_to, text)
            if state == -1:
                return (1, None)
            else:
                state, result = self.__split_translation_into_utterances(result, speakers, turns)
                return (state, result)
        else:
            split_dialogue, split_index = self.__split_text_with_context(dialogue)
            is_length_all_okay = list(map(lambda x: self.__translator.is_length_ok(x), split_dialogue))
            if False in is_length_all_okay:
                return (1, None)
            
            states_and_results = list(map(lambda x: self.__translator.get_translation(lang_from, lang_to, x), split_dialogue))
            states, results = list(zip(*states_and_results))
            
            if -1 in states:
                return (1, None) # timeout
            else:
                state, result = self.__merge_translations(results, split_index, speakers)
                if state == 0:
                    state, result = self.__split_translation_into_utterances(result, speakers, turns)
                return (state, result)

    
    def translate_dialogue_and_handle_errors(self, d, lang_to = None, error_ids = None):
        # TODO: print states here
        # state description
        # 0 := no problem (good!)
        # 1 := translation fail (timeout, max len exceeded, etc)
        # 2 := fail to merge splitted translations
        # 3 := fail to split translation into individual utterances
        # 4 := translation and split done, but turn num before/after translation not matching

        if lang_to is None:
            lang_to = self.default_lang

        lang_from = d["language"]
        turns = d["turns"]
        dialogue = d["conversations"]
        speakers = d["speakers"]

        if turns < 0:
            print_err("\"" +d["id"] + "\"" + " is skipped since sentence length was too long")
            error_ids["sentence_len_too_long"].append(d["id"])
            return {"id": d["id"], "conversations": d["conversations"]}

        state, result = self.__translate_with_context(lang_from, lang_to, dialogue, speakers, turns)

        if state == 1:
            print_err("\"" +d["id"] + "\"" + " failed to translate due to webdriver-related problem")
            error_ids["translator_err"].append(d["id"])
            self.change_driver_to(webdriver.Chrome(DRIVER_PATH))
        elif state == 2:
            print_err("\"" +d["id"] + "\"" + " failed to merge splitted translations")
            error_ids["merging_failure"].append(d["id"])     
        elif state == 3:
            print_err("\"" + d["id"] + "\"" + " failed to split translation into individual utterances")
            error_ids["splitting_failure"].append(d["id"])
        elif state == 4:
            print_err("\"" + d["id"] + "\"" + " turn number does not match before/after translation")
            error_ids["turn_num_not_matching"].append(d["id"])

        return (state, {"id": d["id"], "conversations": result})

    
    def translate_dialogues(self, dialogues, lang_to: str = None, logging_percent: int = 1, start_index: int = 0):
        translations = []
        error_ids = {"turn_num_not_matching": [], "sentence_len_too_long": [], "merging_failure": [], "splitting_failure": [], "translator_err": [], "unknown": []}

        tot_dialogue_num = len(dialogues)
        one_percent_point = int(tot_dialogue_num/100) 

        print_log("Translator", "Translation start. Number of total dialogues: " + str(tot_dialogue_num))

        for i in range(start_index, tot_dialogue_num):
            d = dialogues[i]
            try:
                state, result = self.translate_dialogue_and_handle_errors(d, lang_to, error_ids)
            except KeyboardInterrupt:
                print_log("Translator", "KeyboardInterrupt occured. You should start from index {} (id: {}) next.".format(i, d["id"]))
                return translations, error_ids
            except:
                print_err("\"" + d["id"] + "\"" + " is not translated (unknown exception)")
                error_ids["unknown"].append(d["id"])
                state, result = -1, {"id": d["id"], "conversations": None}

            if state == 0:
                translations.append(result)
            elif self.__include_errs:
                translations.append(result)

            if i % (logging_percent * one_percent_point) == 0 and i != 0:
                print_log("Translator",  str(logging_percent*i/one_percent_point) + "% translated")
        
        return translations, error_ids
