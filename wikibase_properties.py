#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   wikibase_properties.py
#

from constants import PROPERTIES_MATRIX_QUERY
from pathlib import Path
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config

import json
import os.path
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wbi_config['MEDIAWIKI_API_URL'] = yaml_dict['wikibase']['mediawiki_api_url']
wbi_config['SPARQL_ENDPOINT_URL'] = yaml_dict['wikibase']['sparql_endpoint_url']
wbi_config['WIKIBASE_URL'] = yaml_dict['wikibase']['wikibase_url']

def main():
    get_wikibase_properties()

def get_wikibase_properties(wikibase_wikidata_mapping_file='wikibase-wikidata-mapping.json', write_to_file=True, check_for_file=True, update=False):
    
    property_file_name = 'wikibase-properties.json'
    wikibase_properties = {}

    if check_for_file:
        if os.path.isfile(property_file_name):
            with open(property_file_name, 'r') as f:
                wikibase_properties = json.load(f)

    if wikibase_properties and (update == False):
        return wikibase_properties
    
    mapping_dict = None
    with open(wikibase_wikidata_mapping_file, 'r') as f:
        mapping_dict = json.load(f)

    NEW_PROPERTIES_MATRIX_QUERY = PROPERTIES_MATRIX_QUERY % mapping_dict['wikidata_entity_id']['wikibase']

    for mapping, mapping_sub_dict in mapping_dict.items():
        if 'wikidata' in mapping_sub_dict:
            wikidata_id = mapping_sub_dict['wikidata']
            wikibase_id = mapping_sub_dict['wikibase']
            NEW_PROPERTIES_MATRIX_QUERY = NEW_PROPERTIES_MATRIX_QUERY.replace(wikidata_id, wikibase_id)

    all_properties_unformatted = wbi_helpers.execute_sparql_query(NEW_PROPERTIES_MATRIX_QUERY)
    if 'results' in all_properties_unformatted:
        for prop in all_properties_unformatted['results']['bindings']:
            if prop['property']['value'] not in wikibase_properties:
                wikibase_properties[prop['property']['value']] = {
                    'wikibase': str(prop['property']['value']).rsplit('/', 1)[1],
                    'label': prop['propertyLabel']['value'],
                    'datatype': prop['datatype']['value']
                }
                if 'propertyDescription' in prop:
                    wikibase_properties[prop['property']['value']]['desc'] = prop['propertyDescription']['value']
                if 'wikidata' in prop:
                    wikibase_properties[prop['property']['value']]['wikidata'] = prop['wikidata']['value']
            if 'propertyAltLabel' in prop:
                if 'altLabel' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['altLabel'].append(prop['propertyAltLabel']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['altLabel'] = [prop['propertyAltLabel']['value']]
            if 'subjectType' in prop: # TODO: Fix
                if 'subjectType' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['subjectType'].append(prop['subjectType']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['subjectType'] = [prop['subjectType']['value']]
            if 'valueType' in prop: # TODO: Fix
                if 'valueType' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['valueType'].append(prop['valueType']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['valueType'] = [prop['valueType']['value']]
            if 'rangeConstraint' in prop: # TODO: Fix
                if 'rangeConstraint' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['rangeConstraint'].append(prop['rangeConstraint']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['rangeConstraint'] = [prop['rangeConstraint']['value']]
            if 'integerConstraint' in prop: # TODO: Fix
                if 'integerConstraint' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['integerConstraint'].append(prop['integerConstraint']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['integerConstraint'] = [prop['integerConstraint']['value']]
            if 'formatConstraint' in prop: # TODO: Fix
                if 'formatConstraint' in wikibase_properties[prop['property']['value']]:
                    wikibase_properties[prop['property']['value']]['formatConstraint'].append(prop['formatConstraint']['value'])
                else:
                    wikibase_properties[prop['property']['value']]['formatConstraint'] = [prop['formatConstraint']['value']]
            
        if write_to_file:
            with open(property_file_name, 'w') as f:
                json.dump(wikibase_properties, f)
        else:
            return wikibase_properties
    else:
        return wikibase_properties

if __name__ == '__main__':
    main()