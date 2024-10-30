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
import nltk
import textwrap

wikibase_str_text_limit = 400

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

    processed_coi_language = None
    if len(languages) > 1:
        detected_lang = detect_language(str(conflict_of_interest_statement))
        processed_coi_language = detected_lang
    else:
        processed_coi_language = wikibase_language

    tokenizer = determine_tokenizer(str(processed_coi_language))
    sentences = tokenizer.tokenize(str(conflict_of_interest_statement).strip())
    processed_coi = []
    for counter, sentence in enumerate(sentences):
        if len(sentence) > wikibase_str_text_limit:
            sentence = textwrap.shorten(sentence, width=wikibase_str_text_limit)
        coi_sentence = {
            'value': sentence,
            'language': processed_coi_language,
            'P33': counter + 1
        }
        processed_coi.append(coi_sentence)

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

def determine_tokenizer(str):
    wikibase_lang = detect(str)
    punkt = None

    for LA, LA_dict in language_json.items():
        if LA_dict["wikibase"] == wikibase_lang:
            punkt = LA_dict["punkt"]
            break
    if punkt is None:
        print("No value found. Exiting...")
        exit()

    return nltk.data.load('tokenizers/punkt/%s.pickle' % punkt)