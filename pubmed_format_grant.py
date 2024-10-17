#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_grant.py
#

from pathlib import Path
from pubmed_format_country import process_country
from wikibaseintegrator import wbi_login, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists

import constants
import json
import re
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

with open(constants.grants_mapping_file, 'r') as f:
    grants_json = json.load(f)

with open(constants.GR_mapping_file, 'r') as f:
    grant_codes_json = json.load(f)

#
#   GENERAL METHODS
#

def process_grant_list(grant_list_object, wbi):
    grant_list_obj = {}
    for counter, grant in enumerate(grant_list_object):
        grant_complete = None
        try:
            grant_complete = 'Q23075' if str(grant_list_object.attributes['CompleteYN']) == 'Y' else 'Q26205'
        except AttributeError:
            pass

        if 'GrantID' in grant:
            grant_list_obj[grant['GrantID']] = process_grant(grant)
            if grant_complete:
                grant_list_obj[grant['GrantID']]['P812'] = grant_complete

            match_id = check_if_grant_exists(grant['GrantID'])
            if match_id:
                continue_to_add = input("Has this item (%s) already been updated? [Y/n]\n" % (str(match_id)))
                if continue_to_add in ['Y', 'y']:
                    grants_json[grant['GrantID']] = match_id
                    with open(constants.grants_mapping_file, 'w') as f:
                        json.dump(grants_json, f)
                    grant_list_obj[grant['GrantID']][wikibase_name] = match_id
                else:
                    item = add_to_existing_grant(wbi, grant_list_obj[grant['GrantID']], match_id)
                    grant_list_obj[grant['GrantID']][wikibase_name] = str(item.id)
            else:
                item = add_new_grant(wbi, grant_list_obj[grant['GrantID']])
                grant_list_obj[grant['GrantID']][wikibase_name] = str(item.id)
        else:
            grant_list_obj[str(counter)] = process_grant(grant)
            if grant_complete:
                grant_list_obj[str(counter)]['P812'] = grant_complete
            print(grant_list_obj)
            exit()

    return grant_list_obj

# GR: Grant
#
# Based on:
# https://artsci.case.edu/funding/understanding-nih-grant-numbers/
# https://www.nlm.nih.gov/bsd/mms/medlineelements.html#gr
# https://www.nlm.nih.gov/pubs/techbull/mj06/mj06_grant_numbers.html
# https://wayback.archive-it.org/org-350/20210414192512/https://www.nlm.nih.gov/bsd/grant_acronym.html
def process_grant(grant_obj):
    processed_grant_obj = {}

    grant_identifier = grant_id(grant_obj)
    if grant_identifier:
        processed_grant_obj['P809'] = grant_identifier
    grant_funding_mechanism_val = grant_funding_mechanism(grant_obj)
    if grant_funding_mechanism_val:
        processed_grant_obj['P804'] = grant_funding_mechanism_val
    grant_activity_code_val = grant_activity_code(grant_obj)
    if grant_activity_code_val:
        processed_grant_obj['P805'] = grant_activity_code_val
    grant_acronym_val = grant_acronym(grant_obj)
    if grant_acronym_val:
        processed_grant_obj['P810'] = grant_acronym_val
    grant_serial_number_val = grant_serial_number(grant_obj)
    if grant_serial_number_val:
        processed_grant_obj['P807'] = grant_serial_number_val
    grant_agency_val = grant_agency(grant_obj)
    if grant_agency_val:
        processed_grant_obj['P806'] = grant_agency_val
    grant_primary_funding_institute_val = grant_primary_funding_institute(grant_obj)
    if grant_primary_funding_institute_val:
        processed_grant_obj['P811'] = grant_primary_funding_institute_val
    grant_country_val = grant_country(grant_obj)
    if grant_country_val:
        processed_grant_obj['P802'] = grant_country_val # Use country of origin (P802)
        
    return grant_obj

#
#   SUBPROCESS METHODS
#

def grant_id(grant_obj):
    grant_identifier = None
    if 'GrantID' in grant_obj:
        if grant_obj['GrantID'] != "N.A.":
            grant_identifier = (grant_obj['GrantID'].replace(':', '')).split('/')[0]
            if grant_identifier[1] == ' ':
                grant_identifier = grant_identifier.replace(' ', '', 1)
            return grant_identifier
    return grant_identifier

def grant_funding_mechanism(grant_obj):
    grant_funding_mechanism_val = None
    grant_identifier = grant_id(grant_obj)
    if re.match(r'[A-Z]{1}[\d]{2}', grant_identifier):
        grant_funding_mechanism_val = grant_identifier[0]
        grant_activity_code = grant_identifier[0:3]
    return grant_funding_mechanism_val

def grant_activity_code(grant_obj):
    grant_activity_code_val = None
    grant_identifier = grant_id(grant_obj)
    if re.match(r'[A-Z]{1}[\d]{2}', grant_identifier):
        grant_activity_code_val = grant_identifier[0:3]
    return grant_activity_code_val

def grant_acronym(grant_obj):
    grant_acronym_val = None
    grant_identifier = grant_id(grant_obj)
    if 'Acronym' in grant_obj:
        if 'GrantID' in grant_obj:
            if len(grant_obj['Acronym']) > 2:
                if grant_obj['Acronym'] == "GATES":
                    grant_acronym_val = grant_obj['Acronym']
                else:
                    grant_acronym_val = grant_identifier[0:2]
            else:            
                grant_acronym_val = grant_obj['Acronym']
            if grant_acronym_val in grant_identifier:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            else:
                try:
                    grant_acronym_val = (grant_identifier.split(" ")[1])[0:2]
                    grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
                except IndexError:
                    pass
        else:
            grant_acronym_val = grant_obj['Acronym']
    else:
        grant_agency = grant_codes_json[grant_obj['Agency']]
        if "Acronym" in grant_agency:
            grant_acronym_val = grant_agency['Acronym']
            try:
                grant_serial_number = grant_identifier.split(grant_acronym_val)[1]
            except IndexError:
                grant_acronym_val = (grant_identifier.split(' ')[1])[0:2]
    return grant_acronym_val

def grant_serial_number(grant_obj):
    grant_serial_number_val = None
    grant_identifier = grant_id(grant_obj)
    if 'Acronym' in grant_obj:
        if 'GrantID' in grant_obj:
            if len(grant_obj['Acronym']) > 2:
                if grant_obj['Acronym'] == "GATES":
                    grant_acronym_val = grant_obj['Acronym']
                else:
                    grant_acronym_val = grant_identifier[0:2]
            else:            
                grant_acronym_val = grant_obj['Acronym']
            if grant_acronym_val in grant_identifier:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            else:
                try:
                    grant_acronym_val = (grant_identifier.split(" ")[1])[0:2]
                    grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
                except IndexError:
                    pass
        else:
            grant_acronym_val = grant_obj['Acronym']
    else:
        grant_agency_val = grant_codes_json[grant_obj['Agency']]
        if "Acronym" in grant_agency_val:
            grant_acronym_val = grant_agency_val['Acronym']
            try:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            except IndexError:
                grant_acronym_val = (grant_identifier.split(' ')[1])[0:2]
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
    return grant_serial_number_val

def grant_agency(grant_obj):
    grant_agency_val = None
    grant_identifier = grant_id(grant_obj)
    if 'Acronym' in grant_obj:
        if 'GrantID' in grant_obj:
            if len(grant_obj['Acronym']) > 2:
                if grant_obj['Acronym'] == "GATES":
                    grant_acronym_val = grant_obj['Acronym']
                else:
                    grant_acronym_val = grant_identifier[0:2]
            else:            
                grant_acronym_val = grant_obj['Acronym']
            if grant_acronym_val in grant_identifier:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            else:
                try:
                    grant_acronym_val = (grant_identifier.split(" ")[1])[0:2]
                    grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
                except IndexError:
                    pass
        else:
            grant_acronym_val = grant_obj['Acronym']

        grant_agency_hierarchy = grant_obj['Agency'] # Uses abbreviations, full agency hierarchy
        grant_agency_raw = grant_agency_hierarchy.split(' ', 1)[0]
        grant_agency_val = grant_codes_json[grant_acronym_val] # This is always the primary funding institute (awards can be shared but only primary IC is incorporated in the grant application number)

        if grant_agency_val["Institute Acronym"] == grant_agency_raw:
            print(grant_agency_val)
            grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
        else:
            grant_agency_raw = grant_obj['Agency'].split(' ')[1]
            grant_agency_val = grant_codes_json[grant_acronym_val]
            print(grant_agency_raw)
            if grant_agency_val["Institute Acronym"] == grant_agency_raw:
                grant_primary_funding_institute = grant_agency_val[wikibase_name]
            else:
                if grant_obj['Acronym'] in grant_codes_json:
                    grant_primary_funding_institute = grant_agency_val[wikibase_name]
                else:
                    print("Agency (%s) not found. Exiting..." % grant_agency_raw)
                    exit()
    else:
        grant_agency_val = grant_codes_json[grant_obj['Agency']]
        grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
        if "Acronym" in grant_agency_val:
            grant_acronym_val = grant_agency_val['Acronym']
            try:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            except IndexError:
                grant_acronym_val = (grant_identifier.split(' ')[1])[0:2]
                grant_agency_val = grant_codes_json[grant_acronym_val]
                grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
    return grant_agency_val

def grant_primary_funding_institute(grant_obj):
    grant_primary_funding_institute_val = None
    grant_identifier = grant_id(grant_obj)
    if 'Acronym' in grant_obj:
        if 'GrantID' in grant_obj:
            if len(grant_obj['Acronym']) > 2:
                if grant_obj['Acronym'] == "GATES":
                    grant_acronym_val = grant_obj['Acronym']
                else:
                    grant_acronym_val = grant_identifier[0:2]
            else:            
                grant_acronym_val = grant_obj['Acronym']

            if grant_acronym_val in grant_identifier:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            else:
                try:
                    grant_acronym_val = (grant_identifier.split(" ")[1])[0:2]
                    grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
                except IndexError:
                    pass
        else:
            grant_acronym_val = grant_obj['Acronym']

        grant_agency_hierarchy = grant_obj['Agency'] # Uses abbreviations, full agency hierarchy
        grant_agency_raw = grant_agency_hierarchy.split(' ', 1)[0]
        grant_agency_val = grant_codes_json[grant_acronym_val] # This is always the primary funding institute (awards can be shared but only primary IC is incorporated in the grant application number)
        
        if grant_agency_val["Institute Acronym"] == grant_agency_raw:
            grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
        else:
            grant_agency_raw = grant_obj['Agency'].split(' ')[1]
            grant_agency_val = grant_codes_json[grant_acronym]
            if grant_agency["Institute Acronym"] == grant_agency_raw:
                grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
            else:
                if grant_obj['Acronym'] in grant_codes_json:
                    grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
                else:
                    print("Agency (%s) not found. Exiting..." % grant_agency_raw)
                    exit()
    else:
        grant_agency_val = grant_codes_json[grant_obj['Agency']]
        grant_primary_funding_institute_val = grant_agency_val[wikibase_name]
        if "Acronym" in grant_agency_val:
            grant_acronym_val = grant_agency_val['Acronym']
            try:
                grant_serial_number_val = grant_identifier.split(grant_acronym_val)[1]
            except IndexError:
                grant_acronym_val = (grant_identifier.split(' ')[1])[0:2]
                grant_agency_val = grant_codes_json[grant_acronym]
                grant_primary_funding_institute_val = grant_agency_val[wikibase_name]

    return grant_primary_funding_institute_val

def grant_country(grant_obj):
    if 'Country' in grant_obj:
        if grant_obj['Country'] != "":
            return process_country(grant_obj['Country'])
        else:
            return None
    # TODO: Add intermediate process that adds U.S. automatically if from U.S.
    else:
        return None
    
#
#   DETERMINERS METHODS
#


# Add if exists.
def add_to_existing_grant(wbi, processed_grant_object, match_id):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)

    item = wbi.item.get(match_id)

    item.aliases.set('en', processed_grant_object['P809'])

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    grant_instance_of_claim = datatypes.Item(prop_nr="P1", value="Q5185", references=referencesA)
    item.claims.add(grant_instance_of_claim, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

    for claim_id, claim_dict in processed_grant_object.items():
        if claim_id in ["P809", "P810", "P807"]: # String
            claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        elif claim_id in ["P804", "P805", "P806", "P811", "P802"]: # Item
            claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        else:
            print(claim_id)
            print(claim_dict)
            print('here3')
            exit()

        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

    print(item)
    item.write()
    return item

# Add new.
def add_new_grant(wbi, processed_grant_object):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.new()

    item.aliases.set('en', processed_grant_object['P809'])

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    grant_instance_of_claim = datatypes.Item(prop_nr="P1", value="Q5185", references=referencesA)
    item.claims.add(grant_instance_of_claim)

    for claim_id, claim_dict in processed_grant_object.items():
        if claim_id in ["P809", "P810", "P807"]: # String
            claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        elif claim_id in ["P804", "P805", "P806", "P811", "P802"]: # Item
            claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        else:
            print(claim_id)
            print(claim_dict)
            print('here3')
            exit()

        item.claims.add(claim_obj)

    print(item)
    item.write()
    return item

# Check if grant exists.
def check_if_grant_exists(query_str):
    match_id = None
    search_list = wbi_helpers.search_entities(query_str)
    if len(search_list) > 0:
        for search_result in search_list:
            accept_match = input("Is this entity (%s) a match for the grant (%s)? [Y/n]\n" % (str(search_result), str(query_str)))
            if accept_match in ['Y', 'y', 'yes', 'true']:
                match_id = search_result
    if match_id is None:
        accept_match = input("Is there another match you would like to indicate for this grant (%s)? If so, provide it here:\n" % (str(query_str)))
        if accept_match:
            match_id = accept_match.strip()
    return match_id