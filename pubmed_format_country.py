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
    print(country_str)
    return countries_json[country_str][wikibase_name]