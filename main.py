import yaml
import os
import argparse

from modules import ShareGPTJSONProcessor
from modules import ShareGPTTranslator


parser = argparse.ArgumentParser(description="ShareGPT 90k-like data translation")

parser.add_argument('--config', type=str, default="./config.yml")
args = parser.parse_args()

with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


# Your data should be located in:
# ./your_data_path/original

file_list = os.listdir(config["data"] + "original")

if not os.path.isdir(config["data"] + "preprocessed"):
    os.mkdir(config["data"] + "preprocessed")
if not os.path.isdir(config["data"] + "translated"):
    os.mkdir(config["data"] + "translated")
if not os.path.isdir(config["data"] + "error_log"):
    os.mkdir(config["data"] + "error_log")

config["json_processor"]["data"] = config["data"]


Translator = ShareGPTTranslator(config["translator"])

for file in file_list:
    JsonProcessor = ShareGPTJSONProcessor(file, config["json_processor"])
    translations, error_ids = Translator.translate_dialogues(JsonProcessor.dialogues)
    JsonProcessor.save_translations_as_json(translations, error_ids)