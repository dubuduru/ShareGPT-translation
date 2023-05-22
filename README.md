# ShareGPT-translation
Code for translation of [ShareGPT 90k data](https://github.com/lm-sys/FastChat/issues/90).

# How to Use
## Prepare data
Prepare ShareGPT data or other data but in same format of ShareGPT 90k.
Data file (*.json) should be structured in following format:
```json
[
  {
    "id": "some_id",
    "conversations": [
      {
        "from": "human",
        "value": "hello world!"
      },
      {
        "from": "gpt",
        "value": "hello human!"
      },
    ]
  }
]
```
Each dialogue should have `id` and `conversations` as its key values. `conversations` is list of utterances, where each utterance consists of `from` (the name of speaker) and `value` (the contents spoken).

Locate your original json files in `./data/original`, relative path from `main.py`.

## Customize options
You can customize options by modifying `config.yml`.
- `translator`
    - `lang_to`: code of target language of translation. (ex: `en`)
    - `chromedriver`: path for chrome driver, either relative path (from directory of `main.py`) or absolute path.
    - `include_errs`: whether to include not-translated dialogues in output file. If `yes`, dialogues that are not able to be translated would be stored, with well-translated dialogues.
        > Why some dialogues cannot be translated?
        There exsits several reasons that this code cannot tranlsate some dialogues:
        - This code does not split within one sentence. If the length of a sentence exceeds max_length, it simply does not translate the whole dialogue.
        - Chrome webdriver might crash in a sudden. When such bad thing happens, the code skips the dialogue.
        > Why we need `include_errs` option?
        If you want to manually check all the not-translated dialogues and then correct them, this option would be useful. Use error logs in `./data/error_logs` to facilitate such chore.
    - `timeout`: max time to wait for getting translation result from webdriver. (secs)
    - `max_len`: max length of input text, in terms of character and url. **recommended not to change**
    - `overlap`: overlap between input texts. **recommended not to change**
- `json_processor`
    - `use_polyglot`: whether to use python library `polyglot` to detect one source language per dialogue. If `no`, source language is set as "auto", which means google translate automatically detects the source language of input text. It would lead to undesired behaviour; each piece of one dialogue might be translated from different source language. Therefore `yes` is recommended if polyglot is available on your environment.
        > Why `polyglot`?
        `polyglot` seems to be one of the best-performing language-detecting library in terms of accuracy and speed. (see [here](https://stackoverflow.com/questions/39142778/how-to-determine-the-language-of-a-piece-of-text))

## Check the result
Translated files is saved in `./data/translated`. If you want to check which files are not translated and the reason of that, check files in `./data/error_logs`.

## Use preprocessed json
Once you run `main.py` and see the log that indicates the code finished preprocessing of a file, the preprocessed json file is stored in `./data/preprocessed`. So in case you want to re-use preprocessed json files (to re-start the process fast), you can load preprocessed files and skip unnecessary preprocessing. You need to modify `main.py` a bit:
```python
# main.py
...
for file in file_list:
    JsonProcessor = ShareGPTJSONProcessor.from_preprocessed(file)
    translations, error_ids = Translator.translate_dialogues(JsonProcessor.dialogues)
    JsonProcessor.save_translations_as_json(translations, error_ids)
...
```






