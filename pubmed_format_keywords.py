#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_keywords.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.OT_mapping_file, 'r') as f:
    keywords_json = json.load(f)

def process_keywords_list(keyword_array):
    processed_keywords = []
    for keyword_list in keyword_array:
        for keyword in keyword_list:
            processed_keyword = process_keyword(keyword)
            try:
                if 'Owner' in keyword_list.attributes:
                    if keyword_list.attributes['Owner'] == "NOTNLM":
                        processed_keyword['P492'] = 'Q27189'
                    else:
                        print(keyword_list.attributes['Owner'])
                        exit()
            except AttributeError:
                pass
            processed_keywords.append(processed_keyword)
    return processed_keywords

# OT: Other Term
def process_keyword(keyword):
    processed_keyword = {}
    if keyword in keywords_json:
        accept_match = input("Is this entity (%s) a match for the keyword (%s)? [Y/n]\n" % (str(keywords_json[keyword]['lgbtdb']), str(keyword)))
        if accept_match in ['Y', 'y', 'yes', 'true']:
            try:
                processed_keyword = {
                    'value': keywords_json[keyword]['lgbtdb'],
                    'P825': 'Q23075' if str(keyword.attributes['MajorTopicYN']) == 'Y' else 'Q26205'
                }
            except AttributeError:
                pass
        else:
            # TODO: Fix
            keywords_json[keyword] = {}
            with open(constants.OT_mapping_file, 'w') as f:
                json.dump(keywords_json, f, indent=4, sort_keys=True)
            print("Keyword (%s) not found. Please add a mapping to the appropriate JSON file to continue." % str(keyword))
            exit()
    else:
        keywords_json[keyword] = {}
        with open(constants.OT_mapping_file, 'w') as f:
            json.dump(keywords_json, f, indent=4, sort_keys=True)
        print("Keyword (%s) not found. Please add a mapping to the appropriate JSON file to continue." % str(keyword))
        add_to_mapping_file(keyword)
        return process_keyword(keyword)
    
    return processed_keyword

def add_to_mapping_file(keyword_str):
    new_match = input('What is the QID that matches the keyword "%s"?\n' % (str(keyword_str)))
    keywords_json[str(keyword_str)][wikibase_name] = new_match.strip()

    with open(constants.OT_mapping_file, 'w') as f:
        json.dump(keywords_json, f, indent=4, sort_keys=True)

    return new_match