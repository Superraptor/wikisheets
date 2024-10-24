#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_copyright_information.py
#

from langdetect import detect
from pathlib import Path
from pubmed_format_affiliation import check_if_affiliation_exists
from pubmed_format_author import check_if_author_exists
from pubmed_format_language import process_languages, return_wikibase_mapping
from wikidata_mapping import get_wikidata_id

import constants
import json
import re
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.AD_mapping_file, 'r') as f:
    affiliations_json = json.load(f)

with open(constants.AU_mapping_file, 'r') as f:
    authors_json = json.load(f)

with open(constants.LA_mapping_file, 'r') as f:
    language_json = json.load(f)

def process_copyright_information(entrez_obj, copyright_object, from_abstract=False):
    # For example: 'Copyright © 2024 Association of Nurses in AIDS Care.'
    # or '© 2024. The Author(s).'
    # or 'Copyright 2024 American Medical Association. All Rights Reserved.'
    # or 'Published by Elsevier B.V.'
    # or '(PsycInfo Database Record (c) 2024 APA, all rights reserved).'
    # or '© The Author(s) 2024. Published by Oxford University Press on behalf of European Society of Endocrinology.'

    copyright_info_obj = {}

    if isinstance(copyright_object, str):
        copyright_info_obj['P831'] = {
            'value': str(copyright_object.strip()),
        }

        languages = process_languages(entrez_obj['Article']['Language'])
        if len(languages) > 1:
            wikibase_language = []
            for language in languages:
                wikibase_language.append(return_wikibase_mapping(language))
        else:
            wikibase_language = return_wikibase_mapping(languages[0])

        if len(languages) > 1:
            detected_lang = detect_language(str(copyright_object))
            copyright_info_obj['P831']['language'] = detected_lang
        else:
            copyright_info_obj['P831']['language'] = wikibase_language
        
        contains_publisher_info = determine_if_publisher_information(copyright_object)
        contains_copyright_info = determine_if_copyright_information(copyright_object)

        if contains_publisher_info:
            publisher_info = process_publisher_info(copyright_object)
            for publisher_info_id, publisher_info_dict in publisher_info.items():
                copyright_info_obj[publisher_info_id] = publisher_info_dict
        
        if contains_copyright_info:
            copyright_info = process_copyright(entrez_obj, copyright_object)
            for copyright_info_id, copyright_info_dict in copyright_info.items():
                copyright_info_obj[copyright_info_id] = copyright_info_dict
        
        if contains_publisher_info is False and contains_copyright_info is False:
            if copyright_object == entrez_obj['Article']['Abstract']['CopyrightInformation']:
                return copyright_info_obj
            else:
                print("This sentence (%s) appears to not contain copyright or publisher information." % copyright_object)
                exit()
    else:
        print(copyright_object)
        exit()

    return copyright_info_obj

def process_copyright(entrez_obj, copyright_str):
    try:
        processed_copyright_info_str = copyright_str.split('©')[1]
    except IndexError:
        try:
            processed_copyright_info_str = copyright_str.split('Copyright')[1]
        except IndexError:
            try:
                processed_copyright_info_str = copyright_str.split('copyright')[1]
            except IndexError:
                try:
                    processed_copyright_info_str = copyright_str.split('Published by')[1]
                except IndexError:
                    try:
                        processed_copyright_info_str = copyright_str.split('(c)')[1]
                    except IndexError:
                        print("This sentence (%s) appears to not contain copyright information." % copyright_str)
                        exit()

    copyright_info_obj = {}
    copyright_info_obj['P59'] = process_copyright_date(processed_copyright_info_str)
    copyright_info_obj['P450'] = process_copyright_holder(entrez_obj, processed_copyright_info_str)
    return copyright_info_obj

def process_copyright_date(copyright_str):
    date_of_copyright = None
    try:
        date_of_copyright = re.search(r"(\d{4})", copyright_str).group(1)
    except AttributeError:
        pass
    return date_of_copyright

# TODO:
def process_copyright_holder(entrez_obj, copyright_str):
    processed_copyright_holder_list = []
    
    if 'author' in copyright_str.lower() or 'authors' in copyright_str.lower():
        for author in entrez_obj['Article']['AuthorList']:
            match_id = check_if_author_exists(author)
            if match_id:
                processed_copyright_holder_list.append(match_id)
            else:
                full_name = author['ForeName'] + " " + author['LastName']
                list_of_keys = [value for key, value in authors_json.items() if full_name in key.lower()]
                full_name_counter = 1 + len(list_of_keys)
                full_name_with_counter = full_name + ", " + str(full_name_counter)
                print(author)
                # TODO: Open pubmed-authors.json, write author name to the dict,
                # then ask the user to add the mapping. Then exit.
                for key in list_of_keys:

                    accept_match = input("Is this entity (%s) a match for the author name (%s)? [Y/n]\n" % (str(key), str(full_name)))
                    if accept_match in ['Y', 'y', 'yes', 'true']:
                        match_id = authors_json[key][wikibase_name]
                        if match_id:
                            processed_copyright_holder_list.append(match_id)
                        break

                if match_id is None:
                    print("No match found for author (%s). Please add to the appropriate JSON file." % str(full_name))
                    authors_json[full_name_with_counter] = {}
                    if 'Identifier' in author:
                        for identifier in author['Identifier']:
                            try:
                                if 'Source' in identifier.attributes:
                                    if identifier.attributes['Source'] == "ORCID":
                                        authors_json[full_name_with_counter]['ORCID'] = str(identifier)
                                        wikidata_id = get_wikidata_id(str(identifier), id_type="ORCID")
                                        if wikidata_id:
                                            authors_json[full_name_with_counter]['wikidata'] = wikidata_id
                            except AttributeError:
                                pass
                    
                    with open('pubmed-authors.json', 'w') as f:
                        json.dump(authors_json, f, indent=4, sort_keys=True)
                    exit()
    else:
        copyright_holder = copyright_str.split(' ', 1)[1]
        copyright_holder = copyright_str.rsplit(',', 1)[0]

        copyright_holder_str = copyright_holder.strip()
        copyright_holder_id = check_if_affiliation_exists(copyright_holder_str)

        if copyright_holder_id is None:
            if copyright_holder_str in affiliations_json:
                processed_copyright_holder_list.append(affiliations_json[copyright_holder_str][wikibase_name])
            else:
                print("No match found for copyright holder value (%s). Please add to the appropriate JSON file." % str(copyright_holder_str))
                affiliations_json[copyright_holder_str] = {}
                with open('pubmed-affiliation-mappings.json', 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                exit()
        else:
            if copyright_holder_str in affiliations_json:
                processed_copyright_holder_list.append(affiliations_json[copyright_holder_str][wikibase_name])
            else:
                affiliations_json[copyright_holder_str] = {}
                affiliations_json[copyright_holder_str][wikibase_name] = copyright_holder_id
                with open('pubmed-affiliation-mappings.json', 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)

    return processed_copyright_holder_list

# TODO:
def process_publisher_info(copyright_str):
    processed_publisher_info = {}
    print()

    try:
        processed_publisher_info_str = copyright_str.split('Published by')[1]
    except IndexError:
        try:
            processed_publisher_info_str = copyright_str.split('published by')[1]
        except IndexError:
            print("This sentence (%s) appears to not contain publisher information." % copyright_str)
            exit()

    if 'on behalf of' in copyright_str.lower():
        processed_publisher_info_list = processed_publisher_info_str.split('on behalf of')
        on_behalf_of_str = processed_publisher_info_list[1].strip()
        publisher_str = processed_publisher_info_list[0].strip()

        if on_behalf_of_str[-1] == ".":
            on_behalf_of_str = on_behalf_of_str[:-1]

        on_behalf_of_match_id = check_if_affiliation_exists(on_behalf_of_str)

        if on_behalf_of_match_id is None:
            if on_behalf_of_str in affiliations_json:
                on_behalf_of_match_id = affiliations_json[on_behalf_of_str][wikibase_name]
            else:
                print("No match found for on-behalf-of value (%s). Please add to the appropriate JSON file." % str(on_behalf_of_str))
                affiliations_json[on_behalf_of_str] = {}
                with open('pubmed-affiliation-mappings.json', 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                exit()

        publisher_match_id = check_if_affiliation_exists(publisher_str)

        if publisher_match_id is None:
            if publisher_str in affiliations_json:
                publisher_match_id = affiliations_json[publisher_str][wikibase_name]
            else:
                print("No match found for publisher value (%s). Please add to the appropriate JSON file." % str(publisher_str))
                affiliations_json[publisher_str] = {}
                with open('pubmed-affiliation-mappings.json', 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                exit()

        processed_publisher_info['P87'] = publisher_match_id # publisher
        processed_publisher_info['P832'] = on_behalf_of_match_id # on behalf of
    else:
        publisher_str = processed_publisher_info_str.strip()
        publisher_match_id = check_if_affiliation_exists(publisher_str)

        if publisher_match_id is None:
            if publisher_str in affiliations_json:
                publisher_match_id = affiliations_json[publisher_str][wikibase_name]
            else:
                print("No match found for publisher value (%s). Please add to the appropriate JSON file." % str(publisher_str))
                affiliations_json[publisher_str] = {}
                with open('pubmed-affiliation-mappings.json', 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                exit()

        processed_publisher_info['P87'] = publisher_match_id # publisher

    return processed_publisher_info

def determine_if_publisher_information(copyright_str):
    if "published" in copyright_str.lower():
        return True
    else:
        return False

def determine_if_copyright_information(copyright_str):
    if "(c)" in copyright_str.lower():
        return True
    elif "copyright" in copyright_str.lower():
        return True
    elif "©" in copyright_str.lower():
        return True
    elif "copr." in copyright_str.lower():
        return True
    else:
        return False
    
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