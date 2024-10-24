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
    print(mesh_heading_array)
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
                for counter, mesh_qualifier in enumerate(mesh_heading['QualifierName']):
                    processed_mesh_qualifier = process_qualifier_name(mesh_qualifier)
                    processed_mesh_heading[counter] =  {}
                    processed_mesh_heading[counter]['P205'] = processed_mesh_qualifier['P205']
                    processed_mesh_heading[counter]['P829'] = processed_mesh_qualifier['P829']
            else:
                print("TODO: Figure out how to record if there is more than one qualifier. The below attempt is a temporary solution.")
                for counter, mesh_qualifier in enumerate(mesh_heading['QualifierName']):
                    processed_mesh_qualifier = process_qualifier_name(mesh_qualifier)
                    processed_mesh_heading[counter] =  {}
                    processed_mesh_heading[counter]['P205'] = processed_mesh_qualifier['P205']
                    processed_mesh_heading[counter]['P829'] = processed_mesh_qualifier['P829']
    else:
        print(mesh_heading)
        mesh_headings_json[mesh_heading['DescriptorName']] = {"mesh": str(mesh_heading['DescriptorName'].attributes['UI'])}
        with open(constants.MH_mapping_file, 'w') as f:
            json.dump(mesh_headings_json, f, indent=4, sort_keys=True)
        try:
            print("MeSH descriptor name (%s) with the MeSH UID (%s) not found. Please add a mapping to the appropriate JSON file to continue." % (str(mesh_heading['DescriptorName']), str(mesh_heading['DescriptorName'].attributes['UI'])))
            new_match = add_to_mapping_file(str(mesh_heading['DescriptorName']), str(mesh_heading['DescriptorName'].attributes['UI']))
            return process_mesh_heading(mesh_heading)
        except AttributeError:
            exit()

    return processed_mesh_heading

def process_descriptor_name(mesh_heading):
    processed_mesh_descriptor_name = {}
    try:
        processed_mesh_descriptor_name = {
            'value': mesh_headings_json[mesh_heading['DescriptorName']][wikibase_name],
            'P825': 'Q23075' if str(mesh_heading['DescriptorName'].attributes['MajorTopicYN']) == 'Y' else 'Q26205'
        }
        if 'Type' in mesh_heading['DescriptorName'].attributes:
            if mesh_heading['DescriptorName'].attributes['Type'] == 'Geographic':
                processed_mesh_descriptor_name['P816'] = 'Q27278'
            else:
                print(mesh_heading['DescriptorName'])
                exit()
    except KeyError:
        new_match = add_to_mapping_file(mesh_heading['DescriptorName'], mesh_heading['DescriptorName'].attributes['UI'])
        process_descriptor_name(mesh_heading)
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
        except KeyError:
            new_match = add_to_mapping_file(str(mesh_qualifier), str(mesh_qualifier.attributes['UI']))
            return process_qualifier_name(mesh_qualifier)
        except AttributeError:
            pass
    else:
        print(mesh_qualifier)
        mesh_headings_json[str(mesh_qualifier)] = {"mesh": str(mesh_qualifier.attributes['UI'])}
        with open(constants.MH_mapping_file, 'w') as f:
            json.dump(mesh_headings_json, f, indent=4, sort_keys=True)
        try:
            print("MeSH qualifier name (%s) with the MeSH UID (%s) not found. Please add a mapping to the appropriate JSON file to continue." % (str(mesh_qualifier), str(mesh_qualifier.attributes['UI'])))
            new_match = add_to_mapping_file(str(mesh_qualifier), str(mesh_qualifier.attributes['UI']))
            return process_qualifier_name(mesh_qualifier)
        except AttributeError:
            print(mesh_qualifier)
            exit()
    return processed_mesh_qualifier

def add_to_mapping_file(mesh_name, mesh_uid):
    new_match = input('What is the QID that matches the MeSH heading "%s" (%s)?\n' % (str(mesh_name), str(mesh_uid)))
    mesh_headings_json[str(mesh_name)][wikibase_name] = new_match.strip()

    with open(constants.MH_mapping_file, 'w') as f:
        json.dump(mesh_headings_json, f, indent=4, sort_keys=True)

    return new_match