#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_abstract.py
#

from langdetect import detect
from pathlib import Path
from pubmed_format_copyright_information import process_copyright_information

import constants
import json
import nltk.data
import re
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

#
#   DATA DICTIONARIES
#

with open(constants.LA_mapping_file, 'r') as f:
    language_json = json.load(f)

with open(constants.NlmCategory_mapping_file, 'r') as f:
    nlmcategory_json = json.load(f)

#
#   GENERAL METHODS
#

# AB: Abstract
def process_abstract(entrez_obj, abstract_obj):

    if 'CopyrightInformation' in abstract_obj:
        copyright_information = abstract_copyright(entrez_obj, abstract_obj)

    if determine_if_list_abstract(abstract_obj):
        processed_abstract = process_list_abstract(abstract_obj)

    elif determine_if_str_abstract(abstract_obj):
        processed_abstract = process_str_abstract(abstract_obj)

    else:
        print(type(abstract_obj))
        exit()

    print(process_abstract)
    return processed_abstract

def process_list_abstract(abstract_obj):
    if determine_if_structured(abstract_obj):
        processed_abstract_obj = process_list_sentences_structured(abstract_obj)
    else:
        processed_abstract_obj = process_list_sentences_unstructured(abstract_obj)
    return processed_abstract_obj

def process_str_abstract(abstract_obj):
    if determine_if_structured(abstract_obj):
        processed_abstract_obj = process_str_sentences_structured(abstract_obj)
    else:
        processed_abstract_obj = process_str_sentences_unstructured(abstract_obj)
    return processed_abstract_obj

# TODO: For all below, integrate:
# last_sentence = process_copyright_information(sentences[-1])
# and redirect to the pubmed_format_copyright_information file.
def process_list_sentences_structured(abstract_obj, processed_abstract_obj=None):
    if processed_abstract_obj is None:
        processed_abstract_obj = []

    sentence_counter = 1
    wikibase_lang = abstract_lang(abstract_obj)
    tokenizer = determine_tokenizer(abstract_obj)
    truncated = determine_if_truncated(abstract_obj)

    if len(abstract_obj['AbstractText']) > 1:
        for abstract_part in abstract_obj['AbstractText']:
            heading_nlm_category = abstract_heading_nlm_category(abstract_part)
            heading_label = abstract_heading_nlm_category(abstract_part)
            sentences = tokenizer.tokenize(abstract_part)

            for sentence in sentences:
                processed_abstract_sentence_obj = {
                    "value": sentence,
                    "language": wikibase_lang,
                    "P827": {"value": heading_label, "language": wikibase_lang},
                    "P826": heading_nlm_category,
                    "P33": sentence_counter, # series ordinal
                }
                if truncated:
                    processed_abstract_sentence_obj["P790"] = truncated
                processed_abstract_obj.append(processed_abstract_sentence_obj)
                sentence_counter += 1
    else:
        processed_abstract_obj = process_str_sentences_structured(abstract_obj)

    return processed_abstract_obj

def process_str_sentences_structured(abstract_obj, processed_abstract_obj=None):
    if processed_abstract_obj is None:
        processed_abstract_obj = []

    sentence_counter = 1
    abstract_str = abstract_text(abstract_obj)
    wikibase_lang = abstract_lang(abstract_obj)
    unprocessed_headings = abstract_headings(abstract_obj, unprocessed=True)
    processed_headings = abstract_headings(abstract_obj, unprocessed=False)
    tokenizer = determine_tokenizer(abstract_obj)
    truncated = determine_if_truncated(abstract_obj)

    print(unprocessed_headings)

    for counter, heading in enumerate(unprocessed_headings):

        # Get sentences for each section.
        starts_with = heading
        try:
            ends_with = unprocessed_headings[counter+1]
        except IndexError:
            ends_with = None
        print(starts_with)
        print(ends_with)

        # Get string between start and end.
        idx1 = abstract_str.index(starts_with)
        if ends_with:
            idx2 = abstract_str.index(ends_with)
        else:
            idx2 = len(abstract_str)
        print(idx1)
        print(idx2)

        res = ""
        for idx in range(idx1 + len(starts_with), idx2):
            res = res + abstract_str[idx]
        res = res.strip()
        print(res)
        
        sentences = tokenizer.tokenize(res)
        print(sentences)

        for sentence in sentences:
            processed_abstract_sentence_obj = {
                "value": sentence,
                "language": wikibase_lang,
                "P33": sentence_counter, # series ordinal
                "P827": {"value": processed_headings[counter], "language": wikibase_lang}
            }
            if truncated:
                processed_abstract_sentence_obj["P790"] = truncated
            processed_abstract_obj.append(processed_abstract_sentence_obj)
            sentence_counter += 1

    return processed_abstract_obj

def process_list_sentences_unstructured(abstract_obj, processed_abstract_obj=None):
    return process_str_sentences_unstructured(abstract_obj, processed_abstract_obj=processed_abstract_obj)

def process_str_sentences_unstructured(abstract_obj, processed_abstract_obj=None):
    if processed_abstract_obj is None:
        processed_abstract_obj = []

    sentence_counter = 1
    abstract_str = abstract_text(abstract_obj)
    wikibase_lang = abstract_lang(abstract_obj)
    tokenizer = determine_tokenizer(abstract_obj)
    truncated = determine_if_truncated(abstract_obj)

    sentences = tokenizer.tokenize(abstract_str)
    for sentence in sentences:
        processed_abstract_sentence_obj = {
            "value": sentence,
            "language": wikibase_lang,
            "P33": sentence_counter, # series ordinal
        }
        if truncated:
            processed_abstract_sentence_obj["P790"] = truncated
        processed_abstract_obj.append(processed_abstract_sentence_obj)
        sentence_counter += 1

    return processed_abstract_obj

#
#   SUBPROCESS METHODS
#

def abstract_text(abstract_obj):
    if determine_if_list_abstract(abstract_obj):
        if len(abstract_obj['AbstractText']) > 1:
            return str(" ".join(str(abstract_obj['AbstractText'])))
        else:
            return str(abstract_obj['AbstractText'][0])        
    else:
        return str(abstract_obj['AbstractText'])

def abstract_type(abstract_obj):
    abstract_type = None
    try:
        abstract_type = abstract_obj.attributes['Type']
    except KeyError:
        pass
    except AttributeError:
        pass
    return abstract_type

def abstract_lang(abstract_obj):
    abstract_lang = None
    try:
        abstract_lang = abstract_obj.attributes['Language']
    except KeyError:
        pass
    except AttributeError:
        pass

    if abstract_lang is None:
        detected_language = detect(abstract_text(abstract_obj))
    else:
        detected_language = abstract_lang

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

def abstract_copyright(entrez_obj, abstract_obj):
    return process_copyright_information(entrez_obj, abstract_obj["CopyrightInformation"], from_abstract=True)

def abstract_heading_label(abstract_part):
    try:
        return abstract_part.attributes['Label']
    except KeyError:
        return None

def abstract_heading_nlm_category(abstract_part):
    try:
        return nlmcategory_json[abstract_part.attributes['NlmCategory']][wikibase_name]
    except KeyError:
        return None

def abstract_headings(abstract_obj, unprocessed=True):
    headings = []
    if determine_if_structured(abstract_obj):
        if determine_if_list_abstract(abstract_obj):
            for abstract_part in abstract_obj['AbstractText']:
                try:
                    heading = abstract_part.attributes['NlmCategory']
                    headings.append(heading)
                except KeyError:
                    pass
                except AttributeError:
                    pass

    if len(headings) == 0:
        abstract_text_str = abstract_text(abstract_obj)
        if unprocessed:
            if '<b>' in abstract_text_str:
                heading_regex = re.compile('(<b>)([A-Za-z/]{1,20})(</b>)(\: )')
            else:
                heading_regex = re.compile('((\^)|(\.{0,1}\n{0,2}))([\w ]{1,})(\: )')
        else:
            if '<b>' in abstract_text_str:
                heading_regex = re.compile('(<b>)([A-Za-z/]{1,20})(</b>)(\: )')
            else:
                heading_regex = re.compile('((\^)|(\.{0,1}\n{0,2}))([\w ]{1,})(\: )')
        full_headings_found_pre = re.findall(heading_regex, str(abstract_text_str))
        for heading in full_headings_found_pre:
            heading_added = False
            print(heading)
            for char in heading:
                if char.isupper():
                    headings.append(heading)
                    heading_added = True
            if not heading_added:
                if len(heading) == 4:
                    if unprocessed:
                        headings.append(heading[0]+heading[1]+heading[2]+heading[3])
                    else:
                        headings.append(heading[1])

    return headings

#
#   DETERMINER METHODS
#
    
def determine_if_list_abstract(abstract_obj):
    try:
        if isinstance(abstract_obj['AbstractText'], list):
            return True
        else:
            return False
    except TypeError:
        return False

def determine_if_str_abstract(abstract_obj):
    if isinstance(abstract_obj['AbstractText'], list):
        return False
    else:
        return True

def determine_if_truncated(abstract_obj):
    # Determine if abstract is truncated and
    # determine truncation length.
    truncated_at = None
    abstract_str = abstract_text(abstract_obj)
    if "ABSTRACT TRUNCATED AT 250 WORDS" in abstract_str:
        truncated_at = {
            "amount": 250,
            "unit": "Q15883" # word
        }
    elif "ABSTRACT TRUNCATED AT 400 WORDS" in abstract_str:
        truncated_at = {
            "amount": 400,
            "unit": "Q15883" # word
        }
    elif "ABSTRACT TRUNCATED" in abstract_str:
        truncated_at = {
            "amount": 4096,
            "unit": "Q21510" # character
        }
    return truncated_at

def determine_if_structured(abstract_obj):
    headings = []
    if determine_if_list_abstract(abstract_obj):
        for abstract_part in abstract_obj['AbstractText']:
            try:
                heading = abstract_part.attributes['NlmCategory']
                headings.append(heading)
            except KeyError:
                pass
            except AttributeError:
                pass
    if len(headings) == 0:
        abstract_text_str = abstract_text(abstract_obj)
        print(abstract_text_str)
        if '<b>' in abstract_text_str:
            heading_regex = re.compile('(<b>)([A-Za-z/]{1,20})(</b>)')
        else:
            heading_regex = re.compile('((\^)|(\.{0,1}\n{0,2}))([\w ]{1,})(\: )')
        full_headings_found_pre = re.findall(heading_regex, str(abstract_text_str))
        print(heading_regex)
        print(full_headings_found_pre)
        for heading in full_headings_found_pre:
            heading_added = False
            print(heading)
            for char in heading:
                if char.isupper():
                    headings.append(heading)
                    heading_added = True
            if not heading_added:
                if len(heading) == 3:
                    headings.append(heading[1])

    if len(headings) > 0:
        return True
    else:
        return False

def determine_tokenizer(abstract_obj):
    wikibase_lang = abstract_lang(abstract_obj)
    punkt = None

    for LA, LA_dict in language_json.items():
        if LA_dict["wikibase"] == wikibase_lang:
            punkt = LA_dict["punkt"]
            break
    if punkt is None:
        print("No value found. Exiting...")
        exit()

    return nltk.data.load('tokenizers/punkt/%s.pickle' % punkt)