#!/usr/bin/env python

#
#   Clair Kronk
#   22 October 2024
#   pubmed_format_chemicals.py
#

#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_mesh_headings.py
#

from pathlib import Path

import constants
import json
import re
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.MH_mapping_file, 'r') as f:
    mesh_headings_json = json.load(f)

def process_chemical_list(chemical_array):
    processed_chemical_list = []
    for chemical_obj in chemical_array:
        processed_chemical_obj = process_chemical(chemical_obj)
        processed_chemical_list.append(processed_chemical_obj)
    return processed_chemical_list

def process_chemical(chemical_obj):
    processed_chemical_obj = get_substance_name(chemical_obj)
    processed_rn = get_registry_number(chemical_obj)
    for rn_id, rn_val in processed_rn.items():
        processed_chemical_obj[rn_id] = rn_val
    return processed_chemical_obj

# P842 (lgbtDB)
def get_registry_number(chemical_obj):
    processed_chemical_obj = {}
    processed_chemical_obj["P842"] = chemical_obj['RegistryNumber']
    registry_number_type = identify_registry_number_type(str(processed_chemical_obj["P842"]))
    if registry_number_type == "UNII":
        processed_chemical_obj["P845"] = chemical_obj['RegistryNumber']
    elif registry_number_type == "EC":
        processed_chemical_obj["P844"] = chemical_obj['RegistryNumber']
    elif registry_number_type == "CAS":
        processed_chemical_obj["P843"] = chemical_obj['RegistryNumber']
    elif registry_number_type is None:
        pass
    else:
        exit()
    return processed_chemical_obj

def identify_registry_number_type(registry_number_str):
    registry_number_type = None

    cas_regex = re.compile('[1-9]\d{1,6}-\d{2}-\d')
    ec_regex = re.compile('\d\.\d{1,2}\.\d{1,2}\.\d{1,3}')
    unii_regex = re.compile('([0-9A-Za-z]{10}|)')

    if str(registry_number_str) == "0":
        return registry_number_type
    elif unii_regex.match(str(registry_number_str)):
        return "UNII"
    elif ec_regex.match(str(registry_number_str)):
        return "EC"
    elif cas_regex.match(str(registry_number_str)):
        return "CAS"
    else:
        print("Could not identify '%s'. Exiting..." % str(registry_number_str))
        exit()

# See here:
# https://wayback.archive-it.org/org-350/20240424200258/https://www.nlm.nih.gov/bsd/mms/medlineelements.html
#
# Field may identify:
# (1) MeSH SCR chemical and drug terms (Class 1)
# (2) protocol terms (Class 2)
# (3) non-MeSH rare disease terms (Class 3) from the NIH Office of Rare Diseases
# (4) organisms (Class 4) including viruses conforming to the International Committee on Taxonomy of Viruses (ICTV) nomenclature
def get_substance_name(chemical):
    substance_name = str(chemical['NameOfSubstance'])
    mesh_mapping = get_mesh_ui(substance_name)
    processed_substance_name = {
        'P102': substance_name,
        'P846': mesh_mapping
    }
    return processed_substance_name

def get_mesh_ui(substance_name):
    processed_mesh_descriptor_name = {}
    print(substance_name)
    try:
        processed_mesh_descriptor_name = mesh_headings_json[str(substance_name)][wikibase_name]
    except KeyError:
        new_match = add_to_mapping_file(str(substance_name), substance_name.attributes['UI'])
        return get_mesh_ui(substance_name)
    except AttributeError:
        pass
    return processed_mesh_descriptor_name

def add_to_mapping_file(mesh_name, mesh_uid):
    new_match = input('What is the QID that matches the MeSH heading "%s" (%s)?\n' % (str(mesh_name), str(mesh_uid)))
    mesh_headings_json[str(mesh_name)][wikibase_name] = new_match.strip()

    with open(constants.MH_mapping_file, 'w') as f:
        json.dump(mesh_headings_json, f, indent=4, sort_keys=True)

    return new_match