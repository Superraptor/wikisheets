#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_conflict_of_interest_statement.py
#

from langdetect import detect
from pubmed_format_language import process_languages, return_wikibase_mapping

import constants
import json

with open(constants.LA_mapping_file, 'r') as f:
    language_json = json.load(f)

def process_conflict_of_interest_statement(entrez_obj, conflict_of_interest_statement):
    languages = process_languages(entrez_obj['Article']['Language'])
    if len(languages) > 1:
        wikibase_language = []
        for language in languages:
            wikibase_language.append(return_wikibase_mapping(language))
    else:
        wikibase_language = return_wikibase_mapping(languages[0])

    processed_coi = {
        'value': str(conflict_of_interest_statement).strip()
    }

    if len(languages) > 1:
        detected_lang = detect_language(str(conflict_of_interest_statement))
        processed_coi['language'] = detected_lang
    else:
        processed_coi['language'] = wikibase_language

    return processed_coi

def detect_language(str):
    detected_language = detect(str)

    wikibase_lang = None
    for LA, LA_dict in language_json.items():
        if "iso639-1" in LA_dict:
            if LA_dict["iso639-1"] == detected_language:
                punkt = LA_dict["punkt"]
                wikibase_lang = LA_dict["wikibase"]
            elif LA == detected_language:
                punkt = LA_dict["punkt"]
                wikibase_lang = LA_dict["wikibase"]

    return wikibase_lang