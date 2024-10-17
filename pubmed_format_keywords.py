#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_keywords.py
#

import constants
import json

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
            keywords_json[keyword] = {}
            with open('pubmed-keywords.json', 'w') as f:
                json.dump(keywords_json, f, indent=4, sort_keys=True)
            print("Keyword (%s) not found. Please add a mapping to the appropriate JSON file to continue." % str(keyword))
    else:
        keywords_json[keyword] = {}
        with open('pubmed-keywords.json', 'w') as f:
            json.dump(keywords_json, f, indent=4, sort_keys=True)
        print("Keyword (%s) not found. Please add a mapping to the appropriate JSON file to continue." % str(keyword))
    return processed_keyword