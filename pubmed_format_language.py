#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_language.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.LA_mapping_file, 'r') as f:
    language_json = json.load(f)

def process_languages(language_array):
    processed_languages = []
    for language in language_array:
        processed_languages.append(process_language(language))
    return processed_languages

# LA: Language
def process_language(language):
    return language_json[language][wikibase_name]

def return_wikibase_mapping(lgbtdb_id):
    for language_id, language_dict in language_json.items():
        if wikibase_name in language_dict:
            if language_dict[wikibase_name] == lgbtdb_id:
                return language_dict['wikibase']
    return None