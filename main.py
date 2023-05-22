import yaml
import os

from modules import ShareGPTJSONProcessor
from modules import ShareGPTTranslator

with open("./config.yml") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# Your data should be located in:
# ./data/original

file_list = os.listdir("./data/original")

if not os.path.isdir("./data/preprocessed"):
    os.mkdir("./data/preprocessed")
if not os.path.isdir("./data/translated"):
    os.mkdir("./data/translated")
if not os.path.isdir("./data/error_log"):
    os.mkdir("./data/error_log")


Translator = ShareGPTTranslator(config["translator"])

for file in file_list:
    JsonProcessor = ShareGPTJSONProcessor(file, config["json_processor"])
    translations, error_ids = Translator.translate_dialogues(JsonProcessor.dialogues)
    JsonProcessor.save_translations_as_json(translations, error_ids)