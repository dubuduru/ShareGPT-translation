from modules import ShareGPTJSONProcessor
from modules import ShareGPTTranslator

from configs.sg_config import *



Translator = ShareGPTTranslator(LANG_TO)

for i in range(0, FILE_NUM):

    JsonProcessor = ShareGPTJSONProcessor(JSON_PATH[i], PREPROCESS_PATH[i], TRANSLATE_PATH[i], ERROR_LOG_PATH[i])
    translations, error_ids = Translator.translate_dialogues(JsonProcessor.dialogues)
    JsonProcessor.save_translations_as_json(translations, error_ids)