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
    processed_publication_type = {}
    wikibase_instance_of = None
    wikibase_publication_type = None

    try:
        wikibase_instance_of = publication_types_json[publication_type][str(wikibase_name)+'_instance_of']
    except KeyError:
        new_match = add_to_mapping_file(publication_type, "instance_of")
        return process_publication_type(publication_type)

    try:
        wikibase_publication_type = publication_types_json[publication_type][str(wikibase_name)+'_publication_type']
    except KeyError:
        new_match = add_to_mapping_file(publication_type, "publication_type")
        return process_publication_type(publication_type)

    processed_publication_type = {
        "P1": wikibase_instance_of,
        "P799": wikibase_publication_type
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

def add_to_mapping_file(key_name, key_type):
    new_match = None
    if key_type == "instance_of":
        new_match = input('What is the QID that for an instance of "%s" in the Wikibase %s?\n' % (str(key_name), str(wikibase_name)))
    elif key_type == "publication_type":
        new_match = input('What is the QID that for the publication type "%s" in the Wikibase %s?\n' % (str(key_name), str(wikibase_name)))
    else:
        print("The following key type (%s) is not available. Exiting..." % key_type)
        exit()
    publication_types_json[str(key_name)][wikibase_name+'_'+key_type] = new_match.strip()

    with open(constants.PT_mapping_file, 'w') as f:
        json.dump(publication_types_json, f, indent=4, sort_keys=True)

    return new_match