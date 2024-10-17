#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_mesh_headings.py
#

from pathlib import Path

import constants
import json
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.MH_mapping_file, 'r') as f:
    mesh_headings_json = json.load(f)

def process_mesh_headings_list(mesh_heading_array):
    processed_mesh_headings = []
    for mesh_heading in mesh_heading_array:
        processed_mesh_heading = process_mesh_heading(mesh_heading)
        processed_mesh_headings.append(processed_mesh_heading)
    return processed_mesh_headings

# MH: MeSH Terms
def process_mesh_heading(mesh_heading):
    processed_mesh_heading = {}
    if mesh_heading['DescriptorName'] in mesh_headings_json:
        processed_mesh_heading = process_descriptor_name(mesh_heading)
        if len(mesh_heading['QualifierName']) > 0:
            if len(mesh_heading['QualifierName']) == 1:
                for mesh_qualifier in mesh_heading['QualifierName']:
                    processed_mesh_qualifier = process_qualifier_name(mesh_qualifier)
                    processed_mesh_heading['P205'] = processed_mesh_qualifier['P205']
                    processed_mesh_heading['P829'] = processed_mesh_qualifier['P829']
            else:
                print("TODO: Figure out how to record if there is more than one qualifier.")
                print(mesh_heading['QualifierName'])
                exit()
    else:
        mesh_headings_json[mesh_heading['DescriptorName']] = {"mesh": str(mesh_heading.attributes['UI'])}
        with open(constants.MH_mapping_file, 'w') as f:
            json.dump(mesh_headings_json, f, indent=4, sort_keys=True)
        try:
            print("MeSH descriptor name (%s) with the MeSH UID (%s) not found. Please add a mapping to the appropriate JSON file to continue." % (str(mesh_heading['DescriptorName']), str(mesh_heading['DescriptorName'].attributes['UI'])))
        except AttributeError:
            pass
        exit()
    return processed_mesh_heading

def process_descriptor_name(mesh_heading):
    processed_mesh_descriptor_name = {}
    try:
        processed_mesh_descriptor_name = {
            'value': mesh_headings_json[mesh_heading['DescriptorName']][wikibase_name],
            'P825': 'Q23075' if str(mesh_heading['DescriptorName'].attributes['MajorTopicYN']) == 'Y' else 'Q26205'
        }
    except AttributeError:
        pass
    return processed_mesh_descriptor_name

def process_qualifier_name(mesh_qualifier):
    processed_mesh_qualifier = {}
    if str(mesh_qualifier) in mesh_headings_json:
        try:
            processed_mesh_qualifier = {
                'P205': mesh_headings_json[str(mesh_qualifier)][wikibase_name],
                'P829': 'Q23075' if str(mesh_qualifier.attributes['MajorTopicYN']) == 'Y' else 'Q26205'
            }
        except AttributeError:
            pass
    else:
        mesh_headings_json[str(mesh_qualifier)] = {"mesh": str(mesh_qualifier.attributes['UI'])}
        with open(constants.MH_mapping_file, 'w') as f:
            json.dump(mesh_headings_json, f, indent=4, sort_keys=True)
        try:
            print("MeSH qualifier name (%s) with the MeSH UID (%s) not found. Please add a mapping to the appropriate JSON file to continue." % (str(mesh_qualifier), str(mesh_qualifier.attributes['UI'])))
        except AttributeError:
            pass
        exit()
    return processed_mesh_qualifier