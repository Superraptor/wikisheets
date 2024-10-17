#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_citation_subset.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.SB_mapping_file, 'r') as f:
    subset_json = json.load(f)

def process_subsets(subset_array):
    processed_subsets = []
    for subset in subset_array:
        processed_subsets.append(process_subset(subset))
    return processed_subsets

def process_subset(subset):
    return subset_json[subset][wikibase_name]
    