#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_author.py
#

from pathlib import Path
from pubmed_format_affiliation import process_affiliation_list
from pubmed_format_identifier import process_orcid
from wikibaseintegrator import wbi_login, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikidata_mapping import get_wikidata_id

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

with open(constants.AU_mapping_file, 'r') as f:
    authors_json = json.load(f)

# Author List
def process_author_list(author_list_obj):
    processed_author_list = []
    author_counter = 1
    for author_obj in author_list_obj:
        processed_author = process_author(author_obj)
        processed_author['P33'] = author_counter # series ordinal
        print(author_obj)
        print(processed_author)

        try:
            if 'CompleteYN' in author_list_obj.attributes:
                processed_author['P812'] = 'Q23075' if str(author_list_obj.attributes['CompleteYN']) == 'Y' else 'Q26205'
        except KeyError:
            pass
        except AttributeError:
            pass

        try:
            if 'ValidYN' in author_list_obj.attributes:
                processed_author['P812'] = 'Q23075' if str(author_list_obj.attributes['ValidYN']) == 'Y' else 'Q26205'
        except KeyError:
            pass
        except AttributeError:
            pass

        print("HERE1")
        match_id = check_if_author_exists(author_obj)
        print("HERE2")
        if match_id:
            print("HERE2.5")
            continue_to_add = input("Has this item (%s) already been updated? [Y/n]\n" % (str(match_id)))
            if continue_to_add in ['Y', 'y']:
                full_name = author_obj['ForeName'] + " " + author_obj['LastName']
                list_of_keys = [value for key, value in authors_json.items() if full_name in key.lower()]
                full_name_counter = 1 + len(list_of_keys)
                match_key = None
                for key in list_of_keys:
                    accept_match = input("Is this entity (%s) a match for the author name (%s)? [Y/n]\n" % (str(key), str(full_name)))
                    if accept_match in ['Y', 'y', 'yes', 'true']:
                        match_id = authors_json[key]['lgbtdb']
                        if match_id:
                            match_key = key
                            break
                if match_key:
                    authors_json[match_key] = match_id
                else:
                    authors_json[full_name + ", " + str(full_name_counter)] = match_id
                with open(constants.AU_mapping_file, 'w') as f:
                    json.dump(authors_json, f)
                processed_author['lgbtdb'] = match_id
            else:
                item = add_to_existing_author(processed_author, match_id)
                processed_author['lgbtdb'] = str(item.id)
        else:
            print("HERE2.8")
            item = add_new_author(processed_author)
            processed_author['lgbtdb'] = str(item.id)
        print("HERE3")

        processed_author_list.append(processed_author)
        author_counter += 1
        print("HERE4")

    print("HERE5")
    print(processed_author_list)
    print("HERE6")

    return processed_author_list

# AU: Author
def process_author(author_obj):
    processed_author = {
        'P797': {'value': author_obj["ForeName"], 'language': 'en'}, # ForeName
        'P839': {'value': author_obj["LastName"], 'language': 'en'}, # LastName
        'P798': {'value': author_obj["Initials"]} # Initials
    }
    try:
        if 'ValidYN' in author_obj.attributes:
            processed_author['P812'] = 'Q23075' if str(author_obj.attributes['ValidYN']) == 'Y' else 'Q26205'
    except AttributeError:
        pass

    try:
        if 'CompleteYN' in author_obj.attributes:
            processed_author['P812'] = 'Q23075' if str(author_obj.attributes['CompleteYN']) == 'Y' else 'Q26205'
    except KeyError:
        pass
    except AttributeError:
        pass

    processed_ids = process_author_identifiers(author_obj) # TODO: Redirect to pubmed_format_identifier for ORCID
    for processed_id_key, processed_id_val in processed_ids.items():
        processed_author[processed_id_key] = processed_id_val
        if processed_id_key == 'P796':
            wikidata_mapping_for_orcid = get_wikidata_id(processed_id_val, id_type="ORCID")
            if wikidata_mapping_for_orcid:
                processed_author['P3'] = wikidata_mapping_for_orcid

    # Process author affiliations.
    processed_affiliations_val = process_affiliation_list(author_obj['AffiliationInfo'])
    if len(processed_affiliations_val) > 0:
        processed_author['P838'] = processed_affiliations_val

    return processed_author

# AUID: Author Identifier
def process_author_identifiers(author_obj):
    processed_ids = {}

    eidtype = None
    eidvalid = None
    sourceval = None
    for id_in_array in author_obj['Identifier']:
        eidval = str(id_in_array)
        try:
            if 'EIdType' in id_in_array.attributes:
                eidtype = str(id_in_array.attributes['EIdType'])
            if 'ValidYN' in id_in_array.attributes:
                eidvalid = 'Q23075' if str(id_in_array.attributes['ValidYN']) == 'Y' else 'Q26205'
            if 'Source' in id_in_array.attributes:
                sourceval = str(id_in_array.attributes['Source'])
        except AttributeError:
            pass

        if sourceval:
            if sourceval == "ORCID":
                processed_ids['P796'] = eidval
            else:
                print(eidval)
                print(sourceval)
                print("Author identifier (%s) of type %s not recognized. Exiting..." % (str(eidval), str(eidtype)))
                exit()
        else:
            pass

    return processed_ids

# Add if exists.
def add_to_existing_author(processed_author_object, match_id):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.get(match_id)

    full_name = processed_author_object['P797']['value'] + " " + processed_author_object['P839']['value']
    last_name_first = processed_author_object['P839']['value'] + ", " + processed_author_object['P797']['value']

    item.aliases.set('en', full_name)
    item.aliases.set('en', last_name_first)

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    author_instance_of_claim = datatypes.Item(prop_nr="P1", value="Q20846", references=referencesA)
    item.claims.add(author_instance_of_claim, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

    for claim_id, claim_dict in processed_author_object.items():

        if claim_id in ["P798"]: # String
            claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        elif claim_id in ["P797", "P839"]: # MonolingualText
            claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
        elif claim_id in ["P838"]: # Item
            # ??? --> affiliation
            for sub_claim in claim_dict:
                print(sub_claim)
                claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim['lgbtdb'], references=referencesA)
        elif claim_id in ["P796"]: # ExternalID
            claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesA)
        elif claim_id in ["P3"]: # Wikidata mapping
            referencesB = models.references.References()
            referenceB = models.references.Reference()
            referenceB.add(datatypes.Item(prop_nr="P21", value="Q20285")) # stated in; Wikidata
            referenceB.add(datatypes.Item(prop_nr="P278", value="Q27192")) # mapping subject source, mapping from
            referenceB.add(datatypes.Item(prop_nr="P279", value="Q21039")) # mapping object source, mapping to
            referenceB.add(datatypes.Item(prop_nr="P561", value=processed_author_object["P796"]))
            referenceB.add(datatypes.Item(prop_nr="P562", value=claim_dict))
            referencesB.add(referenceB)
            claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], references=referencesB)
        else:
            if claim_id in ['P812', 'P795', 'P33']: # These properties are qualifiers declared in the article, not on the author themself.
                pass
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
def add_new_author(processed_author_object):
    print(processed_author_object)

    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.new()

    full_name = processed_author_object['P797']['value'] + " " + processed_author_object['P839']['value']
    last_name_first = processed_author_object['P839']['value'] + ", " + processed_author_object['P797']['value']

    item.aliases.set('en', full_name)
    item.aliases.set('en', last_name_first)

    referencesA = models.references.References()
    referenceA = models.references.Reference()
    referenceA.add(datatypes.Item(prop_nr="P21", value="Q19463"))
    referencesA.add(referenceA)

    author_instance_of_claim = datatypes.Item(prop_nr="P1", value="Q20846", references=referencesA)
    item.claims.add(author_instance_of_claim)

    for claim_id, claim_dict in processed_author_object.items():

        if claim_id in ["P798"]: # String
            claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
        elif claim_id in ["P797", "P839"]: # MonolingualText
            claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
        elif claim_id in ["P838"]: # Item
            # ??? --> affiliation
            for sub_claim in claim_dict:
                print(sub_claim)
                claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim['lgbtdb'], references=referencesA)
        elif claim_id in ["P796"]: # ExternalID
            print(claim_dict)
            claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesA)
        elif claim_id in ["P3"]: # Wikidata mapping
            referencesB = models.references.References()
            referenceB = models.references.Reference()
            referenceB.add(datatypes.Item(prop_nr="P21", value="Q20285")) # stated in; Wikidata
            referenceB.add(datatypes.Item(prop_nr="P278", value="Q27192")) # mapping subject source, mapping from
            referenceB.add(datatypes.Item(prop_nr="P279", value="Q21039")) # mapping object source, mapping to
            referenceB.add(datatypes.Item(prop_nr="P561", value=processed_author_object["P796"]))
            referenceB.add(datatypes.Item(prop_nr="P562", value=claim_dict))
            referencesB.add(referenceB)
            claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], references=referencesB)
        else:
            if claim_id in ['P812', 'P795', 'P33']: # These properties are qualifiers declared in the article, not on the author themself.
                pass
            else:
                print(claim_id)
                print(claim_dict)
                print('here3')
                exit()

        item.claims.add(claim_obj)

    print(item)
    item.write()
    return item

# Check if author exists (lgbtDB).
def check_if_author_exists(author_obj):
    match_id = None
    full_name = author_obj['ForeName'] + " " + author_obj['LastName']
    last_name_first = author_obj['LastName'] + "," + author_obj['ForeName']
    search_list_1 = wbi_helpers.search_entities(full_name)
    if len(search_list_1) > 0:
        for search_result in search_list_1:
            accept_match = input("Is this entity (%s) a match for the author name (%s)? [Y/n]\n" % (str(search_result), str(full_name)))
            if accept_match in ['Y', 'y', 'yes', 'true']:
                match_id = search_result
    if match_id is None:
        search_list_2 = wbi_helpers.search_entities(last_name_first)
        if len(search_list_2) > 0:
            for search_result in search_list_2:
                accept_match = input("Is this entity (%s) a match for the author name (%s)? [Y/n]\n" % (str(search_result), str(last_name_first)))
                if accept_match in ['Y', 'y', 'yes', 'true']:
                    match_id = search_result
        if match_id is None:
            accept_match = input("Is there another match you would like to indicate for this author name (%s)? If so, provide it here:\n" % (str(full_name)))
            if accept_match:
                match_id = accept_match.strip()
    return match_id