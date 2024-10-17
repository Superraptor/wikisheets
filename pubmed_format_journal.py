#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_journal.py
#

from pathlib import Path
from pubmed_format_country import process_country
from pubmed_format_identifier import process_issn
from pubmed_format_language import process_languages, return_wikibase_mapping
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

wikibase_name = yaml_dict['wikibase']['wikibase_name']

with open(constants.nlm_wikibase_mapping_file, 'r') as f:
    wikibase_mappings_json = json.load(f)

def process_journal(entrez_obj):

    if entrez_obj['MedlineJournalInfo']['NlmUniqueID'] in wikibase_mappings_json:
        match_qid = wikibase_mappings_json[entrez_obj['MedlineJournalInfo']['NlmUniqueID']]
        return match_qid
    else:
        match_qid = check_if_journal_exists(entrez_obj['Article']['Journal']['Title'])
        if match_qid:
            continue_to_add = input("Has this item (%s) already been updated? [Y/n]\n" % (str(match_qid)))
            if continue_to_add in ['Y', 'y']:
                wikibase_mappings_json[entrez_obj['MedlineJournalInfo']['NlmUniqueID']] = match_qid
                with open(constants.nlm_wikibase_mapping_file, 'w') as f:
                    json.dump(wikibase_mappings_json, f)
                return match_qid

    in_database = {
        'value': 'Q19463', # PubMed
    }

    aliases = {}

    # JID: NLM Unique ID
    nlm_unique_id = {
        'value': entrez_obj['MedlineJournalInfo']['NlmUniqueID'],
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }

    # LA: Language
    languages = process_languages(entrez_obj['Article']['Language'])
    wikibase_language = return_wikibase_mapping(languages[0])

    # IS: ISSN
    issn_obj = process_issn(entrez_obj['Article']['Journal']['ISSN'])

    # JT: Journal Title
    journal_title = {
        'value': str(entrez_obj['Article']['Journal']['Title']),
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }
    if len(languages) > 1:
        print()
    else:
        journal_title['language'] = wikibase_language
        if wikibase_language in aliases:
            aliases[wikibase_language].append(str(entrez_obj['Article']['Journal']['Title']))
        else:
            aliases[wikibase_language] = [str(entrez_obj['Article']['Journal']['Title'])]

    # Country
    processed_country = process_country(entrez_obj['MedlineJournalInfo']['Country'])
    country = {
        'value': processed_country,
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }

    # ISO-4 Abbreviation
    iso_4_abbreviation = {
        'value': entrez_obj['Article']['Journal']['ISOAbbreviation'],
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }
    if len(languages) > 1:
        exit()
    else:
        iso_4_abbreviation['language'] = wikibase_language
        if wikibase_language in aliases:
            aliases[wikibase_language].append(str(entrez_obj['Article']['Journal']['ISOAbbreviation']))
        else:
            aliases[wikibase_language] = [str(entrez_obj['Article']['Journal']['ISOAbbreviation'])]

    # MEDLINE Title Abbreviation (MedlineTA)
    medline_ta = {
        'value': entrez_obj['MedlineJournalInfo']['MedlineTA'],
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }
    if len(languages) > 1:
        exit()
    else:
        medline_ta['language'] = wikibase_language
        if wikibase_language in aliases:
            aliases[wikibase_language].append(str(entrez_obj['MedlineJournalInfo']['MedlineTA']))
        else:
            aliases[wikibase_language] = [str(entrez_obj['MedlineJournalInfo']['MedlineTA'])]

    journal = {
        'QID': None,
        'labels': {

        },
        'aliases': aliases,
        'claims': {
            # Instance of; journal
            "P1": {'value': 'Q7205', 'reference': {'P21': 'Q19463' }},

            # Title
            "P67": journal_title,

            # In Database
            'P568': in_database,

            # Country
            "P802": country,

            # NLM Unique ID
            "P803": nlm_unique_id,

            # ISO-4 Abbreviation
            "P800": iso_4_abbreviation,

            # MEDLINE Title Abbreviation (MedlineTA)
            "P801": medline_ta

        }
    }

    # In Languages
    if len(languages) > 1:
        print(languages)
        exit()
    else:
        journal['claims']['P68'] = {
            'value': languages[0],
            'reference': {
                'P21': 'Q19463' # stated in; PubMed
            }
        }

    # ISSN
    if issn_obj:
        for issn_prop, issn_val in issn_obj.items():
            journal['claims'][issn_prop] = {
                'value': issn_val,
                'reference': {
                    'P21': 'Q19463' # stated in; PubMed
                }
            }

    # ISSN-L
    if 'ISSNLinking' in entrez_obj['MedlineJournalInfo']:
        journal['claims']['P526'] = {
            'value': entrez_obj['MedlineJournalInfo']['ISSNLinking'],
            'reference': {
                'P21': 'Q19463' # stated in; PubMed
            }
        }

    journal_wikidata_id = get_wikidata_id(nlm_unique_id['value'], id_type="NLM")
    if journal_wikidata_id:
        journal['claims']['P3'] = {
            'value': journal_wikidata_id,
            'reference': {
                'P21': 'Q20285', # stated in; Wikidata
                'P278': 'Q27165', # mapping subject source, mapping from
                'P279': 'Q21039', # mapping object source, mapping to
                'P561': nlm_unique_id["value"], # mapping subject
                'P562': journal_wikidata_id # mapping object
            }
        }

    print(journal)
    print(match_qid)

    if match_qid:
        add_to_existing_journal(journal, match_qid)
        return match_qid
    else:
        new_id = add_new_journal(journal).id
        return new_id

# Add if exists.
def add_to_existing_journal(processed_journal_object, match_id):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.get(match_id)

    for alias_lang, alias_list in processed_journal_object['aliases'].items():
        for alias in alias_list:
            item.aliases.set(alias_lang, alias)

    for claim_id, claim_dict in processed_journal_object['claims'].items():

        referencesA = models.references.References()
        referenceA1 = models.references.Reference()
        if 'reference' in claim_dict:
            for ref_id, ref_val in claim_dict['reference'].items():
                if ref_id in ['P21', 'P278', 'P279']:
                    referenceA1.add(datatypes.Item(prop_nr=ref_id, value=ref_val))
                elif ref_id in ['P561', 'P562']:
                    print(ref_id)
                    print(ref_val)
                    referenceA1.add(datatypes.ExternalID(prop_nr=ref_id, value=ref_val))
                else:
                    print(ref_id)
                    print(ref_val)
                    print('here1')
                    exit()

            referencesA.add(referenceA1)

            if claim_id in ["P1", "P68", "P568", "P802"]: # Item
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
            elif claim_id in ["P67", "P800", "P801"]: # Monolingual Text
                print(claim_id)
                print(claim_dict)
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
            elif claim_id in ["P3", "P430", "P432", "P433", "P526", "P803"]: # External Identifier
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
            else:
                print(claim_id)
                print(claim_dict)
                print('here2')
                exit()
        else:
            if claim_id in ["P1", "P68", "P568", "P802"]: # Item
                print(claim_id)
                print(claim_dict)
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'])
            elif claim_id in ["P67", "P800", "P801"]: # Monolingual Text
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'])
            elif claim_id in ["P3", "P430", "P432", "P433", "P526", "P803"]: # External Identifier
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'])
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
def add_new_journal(processed_journal_object):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.new()

    for alias_lang, alias_list in processed_journal_object['aliases'].items():
        for alias in alias_list:
            item.aliases.set(alias_lang, alias)

    for claim_id, claim_dict in processed_journal_object['claims'].items():

        referencesA = models.references.References()
        referenceA1 = models.references.Reference()
        if 'reference' in claim_dict:
            for ref_id, ref_val in claim_dict['reference'].items():
                if ref_id in ['P21', 'P278', 'P279']:
                    referenceA1.add(datatypes.Item(prop_nr=ref_id, value=ref_val))
                elif ref_id in ['P561', 'P562']:
                    print(ref_id)
                    print(ref_val)
                    referenceA1.add(datatypes.ExternalID(prop_nr=ref_id, value=ref_val))
                else:
                    print(ref_id)
                    print(ref_val)
                    print('here1')
                    exit()

            referencesA.add(referenceA1)

            if claim_id in ["P1", "P68", "P568", "P802"]: # Item
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
            elif claim_id in ["P67", "P800", "P801"]: # Monolingual Text
                print(claim_id)
                print(claim_dict)
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
            elif claim_id in ["P3", "P430", "P432", "P433", "P526", "P803"]: # External Identifier
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)
            else:
                print(claim_id)
                print(claim_dict)
                print('here2')
                exit()
        else:
            if claim_id in ["P1", "P68", "P568", "P802"]: # Item
                print(claim_id)
                print(claim_dict)
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'])
            elif claim_id in ["P67", "P800", "P801"]: # Monolingual Text
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'])
            elif claim_id in ["P3", "P430", "P432", "P433", "P526", "P803"]: # External Identifier
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'])
            else:
                print(claim_id)
                print(claim_dict)
                print('here3')
                exit()

        item.claims.add(claim_obj)

    print(item)
    item.write()
    return item

# Check if journal exists.
def check_if_journal_exists(query_str):
    match_id = None
    search_list = wbi_helpers.search_entities(query_str)
    if len(search_list) > 0:
        for search_result in search_list:
            accept_match = input("Is this entity (%s) a match for the journal name (%s)? [Y/n]\n" % (str(search_result), str(query_str)))
            if accept_match in ['Y', 'y', 'yes', 'true']:
                match_id = search_result
    if match_id is None:
        accept_match = input("Is there another match you would like to indicate for this journal title (%s)? If so, provide it here:\n" % (str(query_str)))
        if accept_match:
            match_id = accept_match.strip()
    return match_id