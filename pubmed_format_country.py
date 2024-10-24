#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_country.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.PL_mapping_file, 'r') as f:
    countries_json = json.load(f)

def process_country(country_str):
    wikibase_qid = None
    try:
        wikibase_qid = countries_json[country_str][wikibase_name]
    except KeyError:
        wikibase_qid = add_to_mapping_file(country_str)
        process_country(country_str)
    if wikibase_qid is None:
        print(country_str)
        exit()
    return wikibase_qid

def add_to_mapping_file(country_str):
    new_match = input('What is the QID that matches the country "%s"?\n' % (str(country_str)))
    countries_json[str(country_str)][wikibase_name] = new_match.strip()

    with open(constants.PL_mapping_file, 'w') as f:
        json.dump(countries_json, f, indent=4, sort_keys=True)

    return new_match