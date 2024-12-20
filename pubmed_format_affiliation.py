#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_affiliation.py
#

from pathlib import Path
from wikibaseintegrator import wbi_login, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists

import constants
import json
import wikibaseintegrator.datatypes as datatypes
import wikibaseintegrator.wbi_helpers as wbi_helpers
import wikibaseintegrator.models as models
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

full_bot_name = yaml_dict['wikibase']['full_bot_name']
bot_name = yaml_dict['wikibase']['bot_name']
bot_password = yaml_dict['wikibase']['bot_password']

wbi_config['MEDIAWIKI_API_URL'] = yaml_dict['wikibase']['mediawiki_api_url']
wbi_config['SPARQL_ENDPOINT_URL'] = yaml_dict['wikibase']['sparql_endpoint_url']
wbi_config['WIKIBASE_URL'] = yaml_dict['wikibase']['wikibase_url']

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.AD_mapping_file, 'r') as f:
    affiliations_json = json.load(f)

# Affiliation List
# ['AuthorList']['AffiliationInfo']
def process_affiliation_list(affiliation_list_obj):
    processed_affiliation_list = []
    affiliation_counter = 1
    for affiliation_obj in affiliation_list_obj:
        processed_affiliation = process_affiliation(affiliation_obj)
        if isinstance(processed_affiliation[wikibase_name], list):
            for processed_aff_obj in processed_affiliation[wikibase_name]:
                new_processed_affiliation = {}
                new_processed_affiliation[wikibase_name] = processed_aff_obj
                new_processed_affiliation['P33'] = affiliation_counter # series ordinal
                processed_affiliation_list.append(new_processed_affiliation)
                affiliation_counter += 1
        else:
            processed_affiliation['P33'] = affiliation_counter # series ordinal
            processed_affiliation_list.append(processed_affiliation)
            affiliation_counter += 1
    return processed_affiliation_list

# AD: Affiliation
def process_affiliation(affiliation_obj):
    processed_affiliation = {}
    affiliation_id = None

    if 'Identifier' in affiliation_obj:
        if len(affiliation_obj['Identifier']) > 0:
            print(affiliation_obj['Identifier'])
            exit()
    processed_affiliation['value'] = affiliation_obj['Affiliation']

    if affiliation_obj['Affiliation'] in affiliations_json:
        if wikibase_name in affiliations_json[affiliation_obj['Affiliation']]:
            affiliation_id = affiliations_json[affiliation_obj['Affiliation']][wikibase_name]
        else:
            match_id = check_if_affiliation_exists(processed_affiliation['value'])
            if match_id:
                if isinstance(match_id, list):
                    affiliation_id = []
                    for sub_match in match_id:
                        affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = sub_match
                        with open(constants.AD_mapping_file, 'w') as f:
                            json.dump(affiliations_json, f, indent=4, sort_keys=True)
                        affiliation_id.append(affiliations_json[affiliation_obj['Affiliation']][wikibase_name])
                else:
                    affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = match_id
                    with open(constants.AD_mapping_file, 'w') as f:
                        json.dump(affiliations_json, f, indent=4, sort_keys=True)
                    affiliation_id = affiliations_json[affiliation_obj['Affiliation']][wikibase_name]
            else:
                item = add_new_affiliation(processed_affiliation)
                match_id = item.id
                affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = match_id
                with open(constants.AD_mapping_file, 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                affiliation_id = affiliations_json[affiliation_obj['Affiliation']][wikibase_name]
    else:
        affiliations_json[affiliation_obj['Affiliation']] = {}
        match_id = check_if_affiliation_exists(processed_affiliation['value'])
        if match_id:
            if isinstance(match_id, list):
                affiliation_id = []
                for sub_match in match_id:
                    affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = sub_match
                    with open(constants.AD_mapping_file, 'w') as f:
                        json.dump(affiliations_json, f, indent=4, sort_keys=True)
                    affiliation_id.append(affiliations_json[affiliation_obj['Affiliation']][wikibase_name])
            else:
                affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = match_id
                with open(constants.AD_mapping_file, 'w') as f:
                    json.dump(affiliations_json, f, indent=4, sort_keys=True)
                affiliation_id = affiliations_json[affiliation_obj['Affiliation']][wikibase_name]
        else:
            item = add_new_affiliation(processed_affiliation)
            match_id = item.id
            affiliations_json[affiliation_obj['Affiliation']][wikibase_name] = match_id
            with open(constants.AD_mapping_file, 'w') as f:
                json.dump(affiliations_json, f, indent=4, sort_keys=True)
            affiliation_id = affiliations_json[affiliation_obj['Affiliation']][wikibase_name]

        with open(constants.AD_mapping_file, 'w') as f:
            json.dump(affiliations_json, f, indent=4, sort_keys=True)

    if affiliation_id is None:
        print(affiliation_obj)
        exit()
    processed_affiliation[wikibase_name] = affiliation_id
    return processed_affiliation

# Add if exists.
def add_to_existing_affiliation(processed_affiliation_object, match_id):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.get(match_id)

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    item.aliases.set('en', processed_affiliation_object['value'])
    item.write()

    return item

# Add new.
def add_new_affiliation(processed_affiliation_object):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.new()

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    item.aliases.set('en', processed_affiliation_object['value'])
    item.write()

    return item

# Check if affiliation exists.
def check_if_affiliation_exists(query_str):
    match_id = None
    if str(query_str) in affiliations_json:
        if 'wikibase_name' in affiliations_json[str(query_str)]:
            accept_match = input("Is this entity (%s) a match for the affiliation name (%s)? [Y/n]\n" % (str(affiliations_json[str(query_str)][wikibase_name]), str(query_str)))
            if accept_match in ['Y', 'y', 'yes', 'true']:
                match_id = str(affiliations_json[str(query_str)][wikibase_name])
                return match_id
        search_list = wbi_helpers.search_entities(query_str)
        if len(search_list) > 0:
            for search_result in search_list:
                accept_match = input("Is this entity (%s) a match for the affiliation name (%s)? [Y/n]\n" % (str(search_result), str(query_str)))
                if accept_match in ['Y', 'y', 'yes', 'true']:
                    match_id = search_result
                    add_to_mapping_file(query_str, match_id)
    if match_id is None:
        accept_match = input("Is there another match you would like to indicate for this affiliation name (%s)? If so, provide it here:\n" % (str(query_str)))
        if accept_match:
            if ';' in accept_match:
                match_id = []
                preprocessed_match_id_array = accept_match.split(';')
                split_query_str = []
                if ';' in query_str:
                    split_query_str = query_str.split(';')

                for counter, preprocessed_match_id in enumerate(preprocessed_match_id_array):
                    match_id.append(preprocessed_match_id.strip())
                    try:
                        add_to_mapping_file(split_query_str, preprocessed_match_id.strip())
                    except IndexError:
                        pass
            else:
                match_id = accept_match.strip()
                add_to_mapping_file(query_str, match_id)

    return match_id

def add_to_mapping_file(query_str, new_match):
    if str(query_str) not in affiliations_json:
        affiliations_json[str(query_str)] = {}
    affiliations_json[str(query_str)][wikibase_name] = new_match.strip()

    with open(constants.AD_mapping_file, 'w') as f:
        json.dump(affiliations_json, f, indent=4, sort_keys=True)

    return new_match