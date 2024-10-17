#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   wikibase_properties.py
#

from constants import PROPERTIES_LABEL_QUERY, PROPERTY_VALUES_QUERY, WIKIDATA_MAPPING_QUERY
from pathlib import Path
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.wbi_config import config as wbi_config

import json
import os.path
import re
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wbi_config['MEDIAWIKI_API_URL'] = yaml_dict['wikibase']['mediawiki_api_url']
wbi_config['SPARQL_ENDPOINT_URL'] = yaml_dict['wikibase']['sparql_endpoint_url']
wbi_config['WIKIBASE_URL'] = yaml_dict['wikibase']['wikibase_url']

def main():
    wikidata_mapping_property = "P3" # = find_wikidata_mapping_property()
    return_mapping(wikidata_mapping_property)

def return_mapping(wikidata_mapping_property, manifest_file="wikidata-manifest.json", write_to_file=True, check_for_file=True, update=True):

    mapping_file_name = 'wikibase-wikidata-mapping.json'

    mapping_dict = {}
    if check_for_file:
        if os.path.isfile(mapping_file_name):
            with open(mapping_file_name, 'r') as f:
                mapping_dict = json.load(f)

    if mapping_dict and (update == False):
        return mapping_dict
    
    # Write mapping property to dict.
    mapping_dict['wikidata_entity_id'] = {'wikibase': wikidata_mapping_property}

    # Read-in manifest file.
    manifest_data = None
    with open(manifest_file, 'r') as manifest:
        manifest_data = json.load(manifest)

    if manifest_data:

        # Get all QIDs and PIDs from manifest file.
        for prop_name, prop_id in manifest_data['wikibase']['properties'].items():
            mapping_dict[prop_name] = {
                'wikidata': prop_id
            }
        for const_name, const_id in manifest_data['wikibase']['constraints'].items():
            mapping_dict[const_name] = {
                'wikidata': const_id
            }

        # Return all matching QIDs and PIDs using Wikidata mapping property.
        no_match = []
        for entity_name, entity_dict in mapping_dict.items():
            if 'wikidata' in entity_dict:
                FINAL_WIKIDATA_MAPPING_QUERY = WIKIDATA_MAPPING_QUERY % (wikidata_mapping_property, entity_dict['wikidata'])
                wikibase_mapping = wbi_helpers.execute_sparql_query(FINAL_WIKIDATA_MAPPING_QUERY)
                if 'results' in wikibase_mapping:
                    if len(wikibase_mapping['results']['bindings']) >= 1:
                        for match in wikibase_mapping['results']['bindings']:
                            wikibase_iri = match['x']['value']
                            wikibase_id = str(wikibase_iri).rsplit('/', 1)[1]
                            mapping_dict[entity_name]['wikibase'] = wikibase_id
                    else:
                        no_match.append(entity_name)

        # For all non-matches, use named-entity recognition.
        if len(no_match) >= 1:
            print("TODO: Not yet implemented. Exiting...")
            exit()

        # Write out matches to file.
        if write_to_file:
            with open(mapping_file_name, 'w') as f:
                json.dump(mapping_dict, f)
        else:
            return mapping_dict

# This function attempts to find a property
# that represents mappings to Wikidata in your
# Wikibase using named-entity recognition and
# pattern recognition.
def find_wikidata_mapping_property():

    # Step 1. Attempt to find a match for 'Wikidata' in the label or the aliases for the given property,
    # and check that the property has the datatype ExternalId.
    wikibase_properties = wbi_helpers.execute_sparql_query(PROPERTIES_LABEL_QUERY)
    wikidata_property_candidates = {}
    add_property = False
    if 'results' in wikibase_properties:
        for wikibase_property in wikibase_properties['results']['bindings']:
            if 'Wikidata' in wikibase_property['propertyLabel']['value']:
                add_property = True
            if 'propertyDescription' in wikibase_property:
                if 'Wikidata' in wikibase_property['propertyDescription']['value']:
                    add_property = True
            if 'propertyAltLabel' in wikibase_property:
                if 'Wikidata' in wikibase_property['propertyAltLabel']['value']:
                    add_property = True
            if wikibase_property['datatype']['value'] != 'http://wikiba.se/ontology#ExternalId':
                add_property = False
            if add_property:
                wikidata_property_candidates[wikibase_property['property']['value']] = wikibase_property
            add_property = False

    # Step 2. Validate values for this property that fit the expected regular expression.
    regex = r'[QPL][0-9]\d*'
    p = re.compile(regex)
    final_candidates = {}
    for candidate_uri, candidate in wikidata_property_candidates.items():
        candidate_id = str(candidate_uri).rsplit('/', 1)[1]
        final_candidates[candidate_id] = True
        NEW_PROPERTY_VALUES_QUERY = PROPERTY_VALUES_QUERY % candidate_id
        wikibase_property_values = wbi_helpers.execute_sparql_query(NEW_PROPERTY_VALUES_QUERY)
        print(wikibase_property_values)
        if 'results' in wikibase_property_values:
            for property_val in wikibase_property_values['results']['bindings']:
                if p.match(property_val['z']['value']) is None:
                    final_candidates[candidate_id] = False

    # Returns first property ID that matches all criteria above.
    for candidate, candidate_val in final_candidates.items():
        if candidate_val:
            return candidate

if __name__ == '__main__':
    main()