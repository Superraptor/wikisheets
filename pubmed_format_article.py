#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_article.py
#

from wikidata_mapping import get_wikidata_id

from pathlib import Path
from pubmed_format_abstract import process_abstract
from pubmed_format_author import process_author_list
from pubmed_format_citation_subset import process_subsets
from pubmed_format_conflict_of_interest_statement import process_conflict_of_interest_statement
from pubmed_format_date import process_date
from pubmed_format_grant import process_grant_list
from pubmed_format_keywords import process_keywords_list
from pubmed_format_language import process_languages, return_wikibase_mapping
from pubmed_format_mesh_headings import process_mesh_headings_list
from pubmed_format_identifier import process_pmid, process_elocation_ids
from pubmed_format_publication_type import process_publication_type_list
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

with open(constants.pmid_wikibase_mapping_file, 'r') as f:
    wikibase_mappings_json = json.load(f)

def process_article(entrez_obj, journal_id):

    pmid = process_pmid(entrez_obj['PMID'])

    # TI: Title
    article_title = {
        'value': str(entrez_obj['Article']['ArticleTitle']),
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }
    if len(languages) > 1:
        print()
    else:
        article_title['language'] = wikibase_language
        if wikibase_language in aliases:
            aliases[wikibase_language].append(str(entrez_obj['Article']['ArticleTitle']))
        else:
            aliases[wikibase_language] = [str(entrez_obj['Article']['ArticleTitle'])]
            
    if pmid['value'] in wikibase_mappings_json:
        match_qid = wikibase_mappings_json[pmid['value']]
        return match_qid
    else:
        match_qid = check_if_article_exists(article_title['value'])
        if match_qid:
            continue_to_add = input("Has this item (%s) already been updated? [Y/n]\n" % (str(match_qid)))
            if continue_to_add in ['Y', 'y']:
                wikibase_mappings_json[pmid['value']] = match_qid
                with open(constants.pmid_wikibase_mapping_file, 'w') as f:
                    json.dump(wikibase_mappings_json, f)
                return match_qid

    # GN: General Note
    if 'GeneralNote' in entrez_obj:
        if len(entrez_obj['GeneralNote']) > 0:
            print("GeneralNote")
            print(entrez_obj['GeneralNote'])
            exit()
    # IRAD: Investigator Affiliation; IR: Investigator Name; FIR: Full Investigator Name
    if 'InvestigatorList' in entrez_obj:
        if len(entrez_obj['InvestigatorList']) > 0:
            print("InvestigatorList")
            print(entrez_obj['InvestigatorList'])
            exit()
    # OID: Other ID
    if 'OtherID' in entrez_obj:
        if len(entrez_obj['OtherID']) > 0:
            print("OtherID")
            print(entrez_obj['OtherID'])
            exit()
    # SFM: Space Flight Mission
    if 'SpaceFlightMission' in entrez_obj:
        if len(entrez_obj['SpaceFlightMission']) > 0:
            print("SpaceFlightMission")
            print(entrez_obj['SpaceFlightMission'])
            exit()

    in_database_article = {
        'value': 'Q19463', # PubMed
        'P794': process_date(entrez_obj['DateRevised']), # Date last revised (adding as 'date revised' in case there are many revision dates)
        
    }
    indexing_method = str(entrez_obj.attributes['IndexingMethod'])
    if indexing_method == "Automated":
        in_database_article['P834'] = 'Q27177'
    else:
        print(indexing_method)
        exit()
    in_database_status = str(entrez_obj.attributes['Status'])
    if in_database_status == "MEDLINE":
        in_database_article['P835'] = 'Q27187'
    else:
        print(in_database_status)
        exit()
    in_database_owner = str(entrez_obj.attributes['Owner'])
    if in_database_owner == "NLM":
        in_database_article['P492'] = 'Q27188'
    else:
        print(in_database_owner)
        exit()

    if 'Journal' in entrez_obj['Article']:
        if 'JournalIssue' in entrez_obj['Article']['Journal']:
            if 'CitedMedium' in entrez_obj['Article']['Journal']['JournalIssue'].attributes:
                if entrez_obj['Article']['Journal']['JournalIssue'].attributes['CitedMedium'] == 'Internet':
                    in_database_article['P837'] = 'Q1825'
                else:
                    in_database_article['P837'] = 'Q22733'
    
    aliases = {}

    # LA: Language
    languages = process_languages(entrez_obj['Article']['Language'])
    wikibase_language = return_wikibase_mapping(languages[0])

    # OT: Other Term
    keyword_list = process_keywords_list(entrez_obj['KeywordList'])

    citation_subset = process_subsets(entrez_obj['CitationSubset'])

    # DCOM: Date Completed
    # If OLDMEDLINE (OM), DCOM is approximate date record entered PubMed:
    if 'OM' in entrez_obj['CitationSubset']:
        in_database_article['P437'] = process_date(entrez_obj['DateCompleted']) # (Approximate) date record available in PubMed
    else:
        in_database_article['P793'] = process_date(entrez_obj['DateCompleted']) # Date data processing ended

    # VI: Volume
    volume_identifier = {
        'value': entrez_obj['Article']['Journal']['JournalIssue']['Volume'],
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }

    article = {
        'QID': None,
        'labels': {

        },
        'aliases': aliases,
        'claims': {

            # CitationSubset
            'P791': citation_subset,

            # PMID
            'P199': pmid,

            # Published In
            'P307': journal_id,

            # In Database
            'P568': in_database_article,

            # In Language
            'P68': languages,

            # Volume
            'P76': volume_identifier,

            # Article Title
            'P67': article_title,

            # Keyword(s)
            'P136': keyword_list

        }
    }

    # Derived from:
    # https://www.nlm.nih.gov/bsd/licensee/elements_article_source.html
    if 'ArticleDate' in entrez_obj['Article']:
        article['claims']['P836'] = []
        for article_date in entrez_obj['Article']['ArticleDate']:
            article_date_obj = {
                'value': process_date(article_date)
            }
            if 'DateType' in article_date.attributes:
                if article_date.attributes['DateType'] == 'Electronic':
                    article_date_obj['P828'] = 'Q27190'
                else:
                    print(article_date_obj)
                    print(article_date.attributes['DateType'])
                    exit()
            article['claims']['P836'].append(article_date_obj)

    # AB: Abstract
    if 'Abstract' in entrez_obj['Article']:
        article['claims']['P434'] = process_abstract(entrez_obj, entrez_obj['Article']['Abstract'])

    # AID: Article Identifier
    processed_identifiers = process_elocation_ids(entrez_obj['Article']['ELocationID'])
    for identifier_prop_nr, identifier_dict in processed_identifiers.items():
        article['claims'][identifier_prop_nr] = identifier_dict

    # AU: Author
    processed_authors = process_author_list(entrez_obj['Article']['AuthorList'])
    article['claims']['P72'] = []
    for author in processed_authors:
        article['claims']['P72'].append(author)

    # COIS: Conflict of Interest Statement
    if 'CoiStatement' in entrez_obj:
        article['claims']['P833'] = process_conflict_of_interest_statement(entrez_obj['CoiStatement'])

    # GR: Grant Number
    if 'GrantList' in entrez_obj['Article']:
        grant_list = process_grant_list(entrez_obj['Article']['GrantList'])
        article['claims']['P840'] = []
        for grant in grant_list:
            article['claims']['P840'].append(grant)

    # IP: Issue
    if 'Issue' in entrez_obj['Article']['Journal']['JournalIssue']:
        article['claims']['P77'] = entrez_obj['Article']['Journal']['JournalIssue']['Issue']

        # Date Issued
        article['claims']['P469'] = process_date(entrez_obj['Article']['Journal']['JournalIssue']['PubDate'])
        # DP: Date Published
        article['claims']['P58'] = process_date(entrez_obj['Article']['Journal']['JournalIssue']['PubDate'])

    # MH: MeSH Terms
    article['claims']['P206'] = process_mesh_headings_list(entrez_obj['MeshHeadingList'])

    # OAB: Other Abstract
    if 'OtherAbstract' in entrez_obj:
        if len(entrez_obj['OtherAbstract']) > 0:
            article['claims']['P830'] = []
            for other_abs in entrez_obj['OtherAbstract']:
                print(other_abs)
                exit()
                # TODO: Other abstract type?
                article['claims']['P830'].append(process_abstract(other_abs))

    # PG: Pagination
    if 'Pagination' in entrez_obj['Article']:
        article['claims']['P511'] = entrez_obj['Article']['Pagination']['StartPage']
        if 'EndPage' in entrez_obj['Article']['Pagination']:
            article['claims']['P510'] = entrez_obj['Article']['Pagination']['EndPage']
        article['claims']['P57'] = entrez_obj['Article']['Pagination']['MedlinePgn']

    # PT: Publication Type
    processed_publication_types = process_publication_type_list(entrez_obj['Article']['PublicationTypeList'])
    for publication_type in processed_publication_types:
        article['claims']['P1'] = publication_type['P1']
        article['claims']['P799'] = publication_type['P799']

    article_wikidata_id = get_wikidata_id(pmid["value"], id_type="PubMed")
    if article_wikidata_id:
        article['claims']['P3'] = {
            'value': article_wikidata_id,
            'reference': {
                'P21': 'Q20285', # stated in; Wikidata
                'P278': 'Q27165', # mapping subject source, mapping from
                'P279': 'Q21039', # mapping object source, mapping to
                'P561': pmid["value"], # mapping subject
                'P562': article_wikidata_id # mapping object
            }
        }

    print(entrez_obj)
    print(article)
    exit()

    if match_qid:
        add_to_existing_journal(journal, match_qid)
        return match_qid
    else:
        new_id = add_new_journal(journal).id
        return new_id
    
# Add if exists.
def add_to_existing_article(processed_article_object, match_id):
    print()
    
# Add new.
def add_new_article(processed_article_object):
    print()
    
# Check if article exists.
def check_if_article_exists(query_str):
    match_id = None
    search_list = wbi_helpers.search_entities(query_str)
    if len(search_list) > 0:
        for search_result in search_list:
            accept_match = input("Is this entity (%s) a match for the article name (%s)? [Y/n]\n" % (str(search_result), str(query_str)))
            if accept_match in ['Y', 'y', 'yes', 'true']:
                match_id = search_result
    if match_id is None:
        accept_match = input("Is there another match you would like to indicate for this article title (%s)? If so, provide it here:\n" % (str(query_str)))
        if accept_match:
            match_id = accept_match.strip()
    return match_id