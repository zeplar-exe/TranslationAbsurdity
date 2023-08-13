import os
import json
import urllib
import requests
import jsonschema
import re

import plac
import deep_translator

from appdirs import user_data_dir
from bs4 import BeautifulSoup

model_schema = None

with open("model_template.schema.json") as schema_file:
    model_schema = json.loads(schema_file.read())

data_dir = user_data_dir("TranslationAbsurdity", False)
models_dir = os.path.join(data_dir, "models")

if not os.path.exists(data_dir):
    os.mkdir(data_dir)
if not os.path.exists(models_dir):
    os.mkdir(models_dir)

@plac.pos("Target")
@plac.pos("Model")
@plac.pos("Source Language")
@plac.opt("iterations")
def main(target: str, model: str, source_lang="auto", iterations: int=1):
    translate_model = find_model(model)

    if translate_model == None:
        return 1

    def is_url(url):
        return urllib.parse.urlparse(url).scheme != ""

    inputs = {}

    if is_url(target):
        get = requests.get(target)

        get.raise_for_status()

        inputs[target] = BeautifulSoup(get.text, features="html.parser")
    elif os.path.isabs(target) and os.path.exists(target):
        if os.path.isdir(target):
            for f in [f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))]:
                with open(f) as file:
                    inputs[os.path.basename(f)] = file.read()
        else:
            with open(target) as file:
                inputs[os.path.basename(target)] = file.read()
    else:
        relative_path = os.path.join(os.getcwd(), target)
        
        if not os.path.exists(relative_path):
            print("The given target is not a valid URL nor an absolute or relative file path (or it doesn't exist.).")

            return 1
        with open(relative_path) as f:
            inputs[os.path.basename(relative_path)] = f.read()
    
    for i in range(1, iterations + 1):
        for file, text in inputs.copy().items():
            last_lang = source_lang

            for language in translate_model["languages"]:
                translator = deep_translator.GoogleTranslator(source=last_lang, target=language)
                
                if isinstance(inputs[file], BeautifulSoup):
                    soup: BeautifulSoup = inputs[file]

                    for p in soup.find_all("p"):
                        translated = translator.translate(p.get_text())

                        new_p = soup.new_tag("p")
                        new_p.string = translated
                        
                        p.replace_with(new_p)
                else:
                    inputs[file] = translator.translate(text)

                print(f"{file}  |  {last_lang} -> {language}")

                last_lang = language
        
        print(f"Iteration {i} completed.")
    
    for file, text in inputs.items():
        if not os.path.exists("trab_output"):
            os.mkdir("trab_output")
        
        file = re.sub(r'[^\w_. -]', '_', file)

        with open(f"trab_output/{file}.t", "w", encoding="utf-8") as f:
            f.write(str(text))

def models():
    print(f"Models located in '{models_dir}':")

    for f in [f for f in os.listdir(models_dir) if os.path.isfile(os.path.join(models_dir, f))]:
        print(f)

def find_model(name):
    global models_dir, model_schema

    model_file_path = os.path.join(models_dir, name)

    if os.path.exists(model_file_path):
        with open(model_file_path) as f:
            model_json = json.load(f.read())

            jsonschema.validate(model_schema, model_json)

            return model_json

    model_file_path = os.path.join(os.getcwd(), name)
    
    if not os.path.exists(models_dir):
        print(f"The model '{model}' does not exist.")

    with open(model_file_path) as f:
        model_json = json.load(f)

        jsonschema.validate(model_schema, model_json)

        return model_json

plac.call(main)