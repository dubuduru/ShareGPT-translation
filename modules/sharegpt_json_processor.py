import json
import re
import os
from typing import *

import numpy as np

from .log_printer import *

# TODO: print logs in better way ..

class ShareGPTJSONProcessor():
    def __init__(self, file, config, preprocessed = None):
        self.file = file
        self.directory = config["data"]

        self.__use_polyglot = config["use_polyglot"]
        self.__statistics = []

        if preprocessed is None:
            if self.__use_polyglot:
                from polyglot.detect import Detector
            self.dialogues = self.__preprocess()
        
        else:
            # from_preprocessed called
            self.__statistics = preprocessed["statistics"]
            self.dialogues = preprocessed["dialogues"]


    @staticmethod
    def __split_by_sentence(value):
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', value)
        lens = [len(s) for s in sentences]
        if max(lens) >= 5000:
            return [], -1
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

        with open(self.directory + "original/" + self.file, "r") as original_json:
            dict_list = json.load(original_json)
            print_log("JsonProcessor", "Preprocessing", "")

            tot_dialogue_num = len(dict_list)
            ten_percent_point = int(len(dict_list)/10)
            
            for n in range(0, tot_dialogue_num):
                # must have at least 2 elements: "id", "conversations"
                entry = dict_list[n]
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
                    # for statistics - to know lengths of each utterance
                    lengths.append(len(original_convs[i]["value"]))
                    
                    # split a utterance into sentences and concatenate them up to 1000 characters
                    sentences, sent_num = self.__split_by_sentence(original_convs[i]["value"])
                    sentence_nums.append(sent_num)

                    if sent_num == -1:
                        conversations = original_convs[i]["value"]
                        speakers = []
                        turns = -1
                        break
                    for j in range(0, len(sentences)):
                        speaker = original_convs[i]["from"] + str(i) + "_" + str(j)
                        speakers.append(speaker)
                        conversations.append("\"" + speaker + "\"" + ":" + sentences[j])

                # update entry
                entry["conversations"] = conversations
                entry["speakers"] = speakers
                if self.__use_polyglot:
                    entry["language"] = max(set(human_languages), key = human_languages.count)
                    if entry["language"] == "un":
                        entry["language"] = "auto"
                else:
                    entry["language"] = "auto"
                entry["turns"] = turns

                # record statistics
                self.__statistics.append({"id": entry["id"], "lengths": lengths, "sentence_nums": sentence_nums, "turns": turns})

                if n % (ten_percent_point) == 0:
                    print(".", end = "")
            
            print(" Done!")
        
        print_log("JsonProcessor", "Saving preprocessed file ...", end = "")
        with open(self.directory + "preprocessed/" + self.file, "w") as json_file_p:
            json.dump({"dialogues": dict_list, "statistics": self.__statistics, "use_polyglot": self.__use_polyglot}, json_file_p)
        print(" Done!")

        return dict_list

    
    def is_using_polyglot(self):
        return self.__use_polyglot

    
    def view_statistics(self):
        lengths = [l for d in self.__statistics for l in d["lengths"]]
        tot_lengths = [sum(d["lengths"]) + len(d["lengths"]) - 1 for d in self.__statistics]
        sentence_nums = [l for d in self.__statistics for l in d["sentence_nums"]]
        turns = [d["turns"] for d in self.__statistics]
        l_statistics = [np.min(lengths), np.max(lengths), np.mean(lengths), np.std(lengths)]
        tl_statistics = [np.min(tot_lengths), np.max(tot_lengths), np.mean(tot_lengths), np.std(tot_lengths)]
        s_statistics = [np.min(sentence_nums), np.max(sentence_nums), np.mean(sentence_nums), np.std(sentence_nums)]
        t_statistics = [np.min(turns), np.max(turns), np.mean(turns), np.std(turns)]
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["", "min", "max", "mean", "std"]))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["len"]+l_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["tot_len"]+tl_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["sent_num"]+s_statistics))
        print('{:>8} {:>6} {:>6} {:>6} {:>6}'.format(*["turns"]+t_statistics))
    
    
    def save_translations_as_json(self, translations, error_ids):
        print_log("\nJsonProcessor", "Saving the translations to "+ self.directory + "translated/" + self.file +"...", "")
        with open(self.directory + "translated/" + self.file, "w") as json_file_t:
            json.dump(translations, json_file_t, ensure_ascii=False)
        with open(self.directory + "error_log/" + self.file, "w") as json_file_e:
            json.dump(error_ids, json_file_e)
        print(" Done!")

    
    @classmethod
    def from_preprocessed(cls, file, config):
        ## Use this function only if you have preprocessed file made before

        with open(config["data"] + "preprocessed/" + file, "r") as preprocessed:
            print_log("JsonProcessor", "Loading from existing preprocessed file ...", "")
            preprocessed = json.load(preprocessed)
            print(" Done!")
            return cls(file, config, preprocessed)

            


