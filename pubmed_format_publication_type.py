#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_publication_type.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.PT_mapping_file, 'r') as f:
    publication_types_json = json.load(f)

def process_publication_type_list(publication_type_array):
    processed_publication_types = []
    for publication_type in publication_type_array:
        processed_publication_types.append(process_publication_type(publication_type))
    return processed_publication_types

def process_publication_type(publication_type):
    processed_publication_type = {
        "P1": publication_types_json[publication_type][str(wikibase_name)+'_instance_of'],
        "P799": publication_types_json[publication_type][str(wikibase_name)+'_publication_type']
    }

    try:
        pub_model = publication_type.attributes['PubModel']
        if pub_model == "Print":
            processed_publication_type["P828"] = "Q22733"
        else:
            print("This publication model (%s) does not have a mapping. Add one to continue. Exiting..." % pub_model)
            exit()
    except KeyError:
        pass
    except AttributeError:
        pass

    return processed_publication_type