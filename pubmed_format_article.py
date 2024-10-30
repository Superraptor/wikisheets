#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_article.py
#

from langdetect import detect
from pathlib import Path
from pubmed_format_abstract import process_abstract
from pubmed_format_author import process_author_list
from pubmed_format_chemicals import process_chemical_list
from pubmed_format_citation_subset import process_subsets
from pubmed_format_conflict_of_interest_statement import process_conflict_of_interest_statement
from pubmed_format_date import process_date, process_date_range
from pubmed_format_grant import process_grant_list
from pubmed_format_keywords import process_keywords_list
from pubmed_format_language import process_languages, return_wikibase_mapping
from pubmed_format_mesh_headings import process_mesh_headings_list
from pubmed_format_identifier import process_pmid, process_elocation_ids
from pubmed_format_publication_type import process_publication_type_list
from wikibaseintegrator import wbi_login, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists, WikibaseDatePrecision, WikibaseSnakType
from wikidata_mapping import get_wikidata_id

import constants
import json
import wikibaseintegrator.datatypes as datatypes
import wikibaseintegrator.wbi_helpers as wbi_helpers
import wikibaseintegrator.models as models
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

wikibase_name = yaml_dict['wikibase']['wikibase_name']
full_bot_name = yaml_dict['wikibase']['full_bot_name']
bot_name = yaml_dict['wikibase']['bot_name']
bot_password = yaml_dict['wikibase']['bot_password']

wbi_config['MEDIAWIKI_API_URL'] = yaml_dict['wikibase']['mediawiki_api_url']
wbi_config['SPARQL_ENDPOINT_URL'] = yaml_dict['wikibase']['sparql_endpoint_url']
wbi_config['WIKIBASE_URL'] = yaml_dict['wikibase']['wikibase_url']

with open(constants.LA_mapping_file, 'r') as f:
    language_json = json.load(f)

with open(constants.PubModel_mapping_file, 'r') as f:
    pubmodel_mappings_json = json.load(f)

with open(constants.pmid_wikibase_mapping_file, 'r') as f:
    wikibase_mappings_json = json.load(f)

def process_article(entrez_obj, journal_id):

    aliases = {}

    # LA: Language
    print("Processing language entities...")
    languages = process_languages(entrez_obj['Article']['Language'])
    if len(languages) > 1:
        wikibase_language = []
        for language in languages:
            wikibase_language.append(return_wikibase_mapping(language))
    else:
        wikibase_language = return_wikibase_mapping(languages[0])

    print("Processing PubMed identifier...")
    pmid = process_pmid(entrez_obj['PMID'])

    # TI: Title
    print("Processing article title...")
    article_title = {
        'value': str(entrez_obj['Article']['ArticleTitle']),
        'reference': {
            'P21': 'Q19463' # stated in; PubMed
        }
    }
    if len(languages) > 1:
        detected_lang = detect_language(str(entrez_obj['Article']['ArticleTitle']))
        article_title['language'] = detected_lang
        if detected_lang in aliases:
            aliases[detected_lang].append(str(entrez_obj['Article']['ArticleTitle']))
        else:
            aliases[detected_lang] = [str(entrez_obj['Article']['ArticleTitle'])]
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
    print("Processing general notes...")
    if 'GeneralNote' in entrez_obj:
        if len(entrez_obj['GeneralNote']) > 0:
            print("GeneralNote")
            print(entrez_obj['GeneralNote'])
            exit()
    # IRAD: Investigator Affiliation; IR: Investigator Name; FIR: Full Investigator Name
    print("Processing investigators...")
    if 'InvestigatorList' in entrez_obj:
        if len(entrez_obj['InvestigatorList']) > 0:
            print("InvestigatorList")
            print(entrez_obj['InvestigatorList'])
            exit()
    # OID: Other ID
    print("Processing other identifiers...")
    if 'OtherID' in entrez_obj:
        if len(entrez_obj['OtherID']) > 0:
            print("OtherID")
            print(entrez_obj['OtherID'])
            exit()
    # SFM: Space Flight Mission
    print("Processing space flight missions...")
    if 'SpaceFlightMission' in entrez_obj:
        if len(entrez_obj['SpaceFlightMission']) > 0:
            print("SpaceFlightMission")
            print(entrez_obj['SpaceFlightMission'])
            exit()

    print("Processing date last revised...")
    in_database_article = {
        'value': 'Q19463', # PubMed
        'P794': process_date(entrez_obj['DateRevised']), # Date last revised (adding as 'date revised' in case there are many revision dates)
        
    }
    print("Processing indexing method...")
    indexing_method = str(entrez_obj.attributes['IndexingMethod'])
    if indexing_method == "Automated":
        in_database_article['P834'] = 'Q27177'
    elif indexing_method == "Curated":
        in_database_article['P834'] = 'Q27775'
    else:
        print(indexing_method)
        exit()
    print("Processing status...")
    in_database_status = str(entrez_obj.attributes['Status'])
    if in_database_status == "MEDLINE":
        in_database_article['P835'] = 'Q27187'
    else:
        print(in_database_status)
        exit()
    print("Processing owner...")
    in_database_owner = str(entrez_obj.attributes['Owner'])
    if in_database_owner == "NLM":
        in_database_article['P492'] = 'Q27188'
    else:
        print(in_database_owner)
        exit()

    print("Processing journal-related entities...")
    if 'Journal' in entrez_obj['Article']:
        if 'JournalIssue' in entrez_obj['Article']['Journal']:
            if 'CitedMedium' in entrez_obj['Article']['Journal']['JournalIssue'].attributes:
                if entrez_obj['Article']['Journal']['JournalIssue'].attributes['CitedMedium'] == 'Internet':
                    in_database_article['P837'] = 'Q1825'
                else:
                    in_database_article['P837'] = 'Q22733'

    # LA: Language
    #languages = process_languages(entrez_obj['Article']['Language'])
    #wikibase_language = return_wikibase_mapping(languages[0])

    print("Processing citation subset...")
    citation_subset = process_subsets(entrez_obj['CitationSubset'])

    # DCOM: Date Completed
    # If OLDMEDLINE (OM), DCOM is approximate date record entered PubMed:
    print("Processing date completed...")
    if 'OM' in entrez_obj['CitationSubset']:
        in_database_article['P437'] = process_date(entrez_obj['DateCompleted']) # (Approximate) date record available in PubMed
    else:
        in_database_article['P793'] = process_date(entrez_obj['DateCompleted']) # Date data processing ended

    # VI: Volume
    print("Processing volume...")
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
            'P67': article_title

        }
    }

    #try:
    #    publication_model_str = entrez_obj['Article'].attributes['PubModel']
    #    if publication_model_str in pubmodel_mappings_json:
    #        if wikibase_name in pubmodel_mappings_json[publication_model_str]:
    #            article['claims']['P828'] = pubmodel_mappings_json[publication_model_str][wikibase_name]
    #        else:
    #            new_match = add_to_mapping_file(publication_model_str)
    #            article['claims']['P828'] = pubmodel_mappings_json[publication_model_str][wikibase_name]
    #    else:
    #        pubmodel_mappings_json[publication_model_str] = {}
    #        new_match = add_to_mapping_file(publication_model_str)
    #        article['claims']['P828'] = pubmodel_mappings_json[publication_model_str][wikibase_name]
    #except AttributeError:
    #    pass

    # Derived from:
    # https://www.nlm.nih.gov/bsd/licensee/elements_article_source.html
    #print("Processing article date...")
    #if 'ArticleDate' in entrez_obj['Article']:
    #    article['claims']['P836'] = []
    #    if len(entrez_obj['Article']['ArticleDate']) > 0:
    #        for article_date in entrez_obj['Article']['ArticleDate']:
    #            article_date_obj = {
    #                'value': process_date(article_date)
    #            }
    #            if 'DateType' in article_date.attributes:
    #                if article_date.attributes['DateType'] == 'Electronic':
    #                    article_date_obj['P828'] = 'Q27190'
    #                else:
    #                    print(article_date_obj)
    #                    print(article_date.attributes['DateType'])
    #                    exit()
    #        article['claims']['P836'].append(article_date_obj)
    #    else:
    #        article['claims']['P836'].append("UNKNOWN")

    # AB: Abstract
    #print("Processing abstract...")
    #if 'Abstract' in entrez_obj['Article']:
    #    article['claims']['P434'] = process_abstract(entrez_obj, entrez_obj['Article']['Abstract'])

    # AID: Article Identifier
    #print("Processing article identifiers...")
    #processed_identifiers = process_elocation_ids(entrez_obj['Article']['ELocationID'])
    #for identifier_prop_nr, identifier_dict in processed_identifiers.items():
    #    article['claims'][identifier_prop_nr] = identifier_dict

    # AU: Author
    #print("Processing authors...")
    #processed_authors = process_author_list(entrez_obj['Article']['AuthorList'])
    #article['claims']['P72'] = []
    #for author in processed_authors:
    #    article['claims']['P72'].append(author)

    # COIS: Conflict of Interest Statement
    #print("Processing conflict-of-interest statement...")
    #if 'CoiStatement' in entrez_obj:
    #    article['claims']['P833'] = process_conflict_of_interest_statement(entrez_obj, entrez_obj['CoiStatement'])

    # GR: Grant Number
    #print("Processing grants...")
    #if 'GrantList' in entrez_obj['Article']:
    #    grant_list = process_grant_list(entrez_obj, entrez_obj['Article']['GrantList'])
    #    article['claims']['P840'] = []
    #    for grant_id, grant_dict in grant_list.items():
    #        article['claims']['P840'].append(grant_dict)

    # IP: Issue
    #print("Processing journal issue...")
    #if 'Issue' in entrez_obj['Article']['Journal']['JournalIssue']:
    #    article['claims']['P77'] = entrez_obj['Article']['Journal']['JournalIssue']['Issue']

    #if 'PubDate' in entrez_obj['Article']['Journal']['JournalIssue']:
    #    if 'Year' in entrez_obj['Article']['Journal']['JournalIssue']['PubDate']:
    #        # Date Issued
    #        article['claims']['P469'] = process_date(entrez_obj['Article']['Journal']['JournalIssue']['PubDate'])
    #        # DP: Date Published
    #        article['claims']['P58'] = process_date(entrez_obj['Article']['Journal']['JournalIssue']['PubDate'])

    #    elif 'MedlineDate' in entrez_obj['Article']['Journal']['JournalIssue']['PubDate']:
    #        article['claims']['P469'] = process_date_range(entrez_obj['Article']['Journal']['JournalIssue']['PubDate']['MedlineDate'])
    #        article['claims']['P58'] = process_date_range(entrez_obj['Article']['Journal']['JournalIssue']['PubDate']['MedlineDate'])

    # MH: MeSH Terms
    print("Processing MeSH terms...")
    article['claims']['P206'] = process_mesh_headings_list(entrez_obj['MeshHeadingList'])

    # NM: Substance Name
    # RN: Registry Number/EC Number
    print("Processing chemical list (substance names, registry numbers)...")
    if 'ChemicalList' in entrez_obj:
        if len(entrez_obj['ChemicalList']) > 0:
            article['claims']['P846'] = process_chemical_list(entrez_obj['ChemicalList'])

    # OAB: Other Abstract
    #print("Processing other abstracts...")
    #if 'OtherAbstract' in entrez_obj:
    #    if len(entrez_obj['OtherAbstract']) > 0:
    #        article['claims']['P830'] = []
    #        for other_abs in entrez_obj['OtherAbstract']:
    #            print(other_abs)
    #            other_abs_obj = process_abstract(entrez_obj, other_abs)
    #            article['claims']['P830'].append(other_abs_obj)

    # OT: Other Term
    print("Processing keywords...")
    if "KeywordList" in entrez_obj:
        if len(entrez_obj['KeywordList']) > 0:
            keyword_list = process_keywords_list(entrez_obj['KeywordList'])
            article['claims']['P136'] = keyword_list

    # PG: Pagination
    #print("Processing pagination...")
    #if 'Pagination' in entrez_obj['Article']:
    #    article['claims']['P511'] = entrez_obj['Article']['Pagination']['StartPage']
    #    if 'EndPage' in entrez_obj['Article']['Pagination']:
    #        article['claims']['P510'] = entrez_obj['Article']['Pagination']['EndPage']
    #    article['claims']['P57'] = entrez_obj['Article']['Pagination']['MedlinePgn']

    # PT: Publication Type
    print("Processing publication types...")
    processed_publication_types = process_publication_type_list(entrez_obj['Article']['PublicationTypeList'])
    for publication_type in processed_publication_types:
        article['claims']['P1'] = publication_type['P1']
        article['claims']['P799'] = publication_type['P799']

    # TT: Transliterated Title (Vernacular Title)
    #print("Processing vernacular title...")
    #if 'VernacularTitle' in entrez_obj['Article']:
    #    vernacular_title = {
    #        'value': str(entrez_obj['Article']['VernacularTitle']),
    #        'reference': {
    #            'P21': 'Q19463' # stated in; PubMed
    #        }
    #    }
    #    if len(languages) > 1:
    #        detected_lang = detect_language(str(entrez_obj['Article']['VernacularTitle']))
    #        vernacular_title['language'] = detected_lang
    #        if detected_lang in aliases:
    #            aliases[detected_lang].append(str(entrez_obj['Article']['VernacularTitle']))
    #        else:
    #            aliases[detected_lang] = [str(entrez_obj['Article']['VernacularTitle'])]
    #    else:
    #        vernacular_title['language'] = wikibase_language
    #        if wikibase_language in aliases:
    #            aliases[wikibase_language].append(str(entrez_obj['Article']['VernacularTitle']))
    #        else:
    #            aliases[wikibase_language] = [str(entrez_obj['Article']['VernacularTitle'])]
    #    article['claims']['P841'] = vernacular_title

    #print("Attempting to map to Wikidata...")
    #article_wikidata_id = get_wikidata_id(pmid["value"], id_type="PubMed")
    #if article_wikidata_id:
    #    article['claims']['P3'] = {
    #        'value': article_wikidata_id,
    #        'reference': {
    #            'P21': 'Q20285', # stated in; Wikidata
    #            'P278': 'Q27165', # mapping subject source, mapping from
    #            'P279': 'Q21039', # mapping object source, mapping to
    #            'P561': pmid["value"], # mapping subject
    #            'P562': article_wikidata_id # mapping object
    #        }
    #    }

    print(entrez_obj)
    print(article)

    #if match_qid:
    #    add_to_existing_article(article, match_qid)
    #    return match_qid
    #else:
    #    new_id = add_new_article(article).id
    #    return new_id
    
# Add if exists.
def add_to_existing_article(processed_article_object, match_id):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.get(match_id)

    for alias_lang, alias_list in processed_article_object['aliases'].items():
        for alias in alias_list:
            item.aliases.set(alias_lang, alias)

    for claim_id, claim_dict in processed_article_object['claims'].items():
        already_appended = False

        referencesA = models.references.References()
        referenceA1 = models.references.Reference()
        referenceA1.add(datatypes.Item(prop_nr='P21', value='Q19463'))
        referencesA.add(referenceA1)

        if claim_id in ["P1", "P68", "P72", "P136", "P206", "P307", "P568", "P791", "P799", "P828", "P840", "P846"]: # Item
            if isinstance(claim_dict, str):
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict, references=referencesA)
            elif isinstance(claim_dict, list):
                if isinstance(claim_dict[0], str):
                    for sub_claim in claim_dict:
                        claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
                elif isinstance(claim_dict[0], dict):
                    for sub_claim_dict in claim_dict:
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim_dict.items():
                            if qual_claim_id in ["P816", "P825", "P492"]: # Item
                                qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P842"]: # String
                                qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P843", "P844", "P845"]: # ExternalID
                                qualifiers.add(datatypes.ExternalID(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif isinstance(qual_claim_val, dict) and claim_id == 'P206':
                                for qual_sub_claim_id, qual_sub_claim_val in qual_claim_val.items():
                                    if qual_sub_claim_id in ["P205", "P829"]: # Item
                                        qualifiers.add(datatypes.Item(prop_nr=qual_sub_claim_id, value=qual_sub_claim_val))
                            elif isinstance(qual_claim_val, str) and claim_id == 'P72':
                                if qual_claim_id in ["P812"]: # Item
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif isinstance(qual_claim_val, dict) and claim_id == 'P72':
                                if qual_claim_id in ["P797", "P839"]: # Monolingual Text
                                    qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                                elif qual_claim_id in ["P798"]: # String
                                    qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val['value']))
                            elif isinstance(qual_claim_val, int) and claim_id == 'P72':
                                if qual_claim_id in ["P33"]: # Quantity
                                    qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                            elif isinstance(qual_claim_val, list) and claim_id == 'P72':
                                if qual_claim_id in ["P838"]: # Item
                                    for affiliation in qual_claim_val:
                                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=affiliation[wikibase_name]))
                        print(qualifiers)
                        if 'value' in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict['value'], qualifiers=qualifiers, references=referencesA)
                        elif wikibase_name in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict[wikibase_name], qualifiers=qualifiers, references=referencesA)
                        elif 'P846' in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict['P846'], qualifiers=qualifiers, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
            elif isinstance(claim_dict, dict):
                qualifiers = models.Qualifiers()
                for qual_claim_id, qual_claim_val in claim_dict.items():
                    if qual_claim_id in ["P793", "P794"]: # Time
                        qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY))
                    elif qual_claim_id in ["P492", "P834", "P835", "P837"]: # Item
                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], qualifiers=qualifiers, references=referencesA)
            else:
                print(claim_id)
                print(claim_dict)
                exit()

        elif claim_id in ["P67", "P434", "P830", "P833", "P841"]: # Monolingual Text
            if isinstance(claim_dict, list):
                if isinstance(claim_dict[0], dict):
                    for sub_claim_dict in claim_dict:
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim_dict.items():
                            if qual_claim_id in ["P33"]: # Quantity
                                qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                            elif qual_claim_id in ["P87", "P816", "P826", "P832"]: # Item
                                if qual_claim_val is None:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, snaktype=WikibaseSnakType.NO_VALUE))
                                else:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P827", "P831"]: # MonolingualText
                                qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                            elif qual_claim_id in ["P59"]: # Time
                                qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'-00-00'+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR))
                            elif qual_claim_id in ["P450"]: # Item
                                for sub_item in qual_claim_val:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=sub_item))
                        claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=sub_claim_dict['value'], language=sub_claim_dict['language'], qualifiers=qualifiers, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
                elif isinstance(claim_dict[0], list):
                    print(claim_id)
                    if isinstance(claim_dict[0][0], dict):
                        for sub_claim_dict in claim_dict:
                            for infra_claim_dict in sub_claim_dict:
                                qualifiers = models.Qualifiers()
                                for qual_claim_id, qual_claim_val in infra_claim_dict.items():
                                    if qual_claim_id in ["P33"]: # Quantity
                                        qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                                    elif qual_claim_id in ["P87", "P816", "P826", "P832"]:
                                        if qual_claim_val is None:
                                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, snaktype=WikibaseSnakType.NO_VALUE))
                                        else:
                                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                                    elif qual_claim_id in ["P827"]:
                                        qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=infra_claim_dict['value'], language=infra_claim_dict['language'], qualifiers=qualifiers, references=referencesA)
                                item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                                already_appended = True
                    else:
                        print(claim_id)
                        print(claim_dict)
                        exit()
                else:
                    print(claim_id)
                    print(claim_dict)
                    exit()
            elif isinstance(claim_dict, dict):
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
            else:
                print(claim_id)
                print(claim_dict)
                exit()

        elif claim_id in ["P3", "P95", "P199"]: # External Identifier
            if claim_id == "P3":
                referencesB = models.references.References()
                referenceB1 = models.references.Reference()
                for ref_id, ref_val in claim_dict['reference'].items():
                    if ref_id in ['P21', 'P278', 'P279']:
                        referenceB1.add(datatypes.Item(prop_nr=ref_id, value=ref_val))
                    elif ref_id in ['P561', 'P562']:
                        referenceB1.add(datatypes.String(prop_nr=ref_id, value=ref_val))
                referencesB.add(referenceB1)
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesB)
            else:
                if isinstance(claim_dict, str):
                    claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesA)
                elif isinstance(claim_dict, list):
                    print(claim_id)
                    print(claim_dict)
                    exit()
                elif isinstance(claim_dict, dict):
                    qualifiers = models.Qualifiers()
                    for qual_claim_id, qual_claim_val in claim_dict.items():
                        if qual_claim_id in ["P792"]: # String
                            qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val))
                        elif qual_claim_id in ["P795"]: # Item
                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                    claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], qualifiers=qualifiers, references=referencesA)
                else:
                    print(claim_id)
                    print(claim_dict)
                    exit()

        elif claim_id in ["P57", "P76", "P77", "P510", "P511", "P808"]: # String
            if isinstance(claim_dict, str):
                claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict, references=referencesA)
            elif isinstance(claim_dict, list):
                print(claim_id)
                print(claim_dict)
                exit()
            elif isinstance(claim_dict, dict):
                claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)

        elif claim_id in ["P58", "P469", "P836"]: # Time
            if isinstance(claim_dict, str):
                if claim_dict == "UNKNOWN":
                    claim_obj = datatypes.Time(prop_nr=claim_id, snaktype=WikibaseSnakType.UNKNOWN_VALUE, references=referencesA)
                else:
                    if "-00-00" in str(claim_dict):
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR, references=referencesA)
                    elif "-00" in str(claim_dict):
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.MONTH, references=referencesA)
                    else:
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, references=referencesA)
            elif isinstance(claim_dict, list):
                for sub_claim in claim_dict:
                    
                    if isinstance(sub_claim, dict):
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim.items():
                            if qual_claim_id in ["P828"]: # Item
                                qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(sub_claim['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, qualifiers=qualifiers, references=referencesA)
                    elif isinstance(sub_claim, str):
                        if sub_claim == "UNKNOWN":
                            claim_obj = datatypes.Time(prop_nr=claim_id, snaktype=WikibaseSnakType.UNKNOWN_VALUE, references=referencesA)
                        else:
                            claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(sub_claim['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, references=referencesA)
                    item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                    already_appended = True
            elif isinstance(claim_dict, dict):
                qualifiers = models.Qualifiers()
                for qual_claim_id, qual_claim_val in claim_dict.items():
                    if qual_claim_id in ["P828"]: # Item
                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                    elif qual_claim_id in ["P847", "P848"]:
                        qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY))
                if 'precision' in claim_dict:
                    if claim_dict['precision'] == "YEAR":
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR, qualifiers=qualifiers, references=referencesA)
                    elif claim_dict['precision'] == "MONTH":
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.MONTH, qualifiers=qualifiers, references=referencesA)
                    else:
                        print("Precision value not recognized. Exiting...")
                        exit()
                else:
                    claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, qualifiers=qualifiers, references=referencesA)
        else:
            print(claim_id)
            print(claim_dict)
            print('here2')
            exit()

        if not already_appended:
            item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

    #print(item)
    item.write()

    exit()
    
# Add new.
def add_new_article(processed_article_object):
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    wbi = WikibaseIntegrator(login=login_instance)
    item = wbi.item.new()

    for alias_lang, alias_list in processed_article_object['aliases'].items():
        for alias in alias_list:
            item.aliases.set(alias_lang, alias)

    for claim_id, claim_dict in processed_article_object['claims'].items():
        already_appended = False

        referencesA = models.references.References()
        referenceA1 = models.references.Reference()
        referenceA1.add(datatypes.Item(prop_nr='P21', value='Q19463'))
        referencesA.add(referenceA1)

        if claim_id in ["P1", "P68", "P72", "P136", "P206", "P307", "P568", "P791", "P799", "P828", "P840", "P846"]: # Item
            if isinstance(claim_dict, str):
                claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict, references=referencesA)
            elif isinstance(claim_dict, list):
                if isinstance(claim_dict[0], str):
                    for sub_claim in claim_dict:
                        claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
                elif isinstance(claim_dict[0], dict):
                    for sub_claim_dict in claim_dict:
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim_dict.items():
                            if qual_claim_id in ["P816", "P825", "P492"]: # Item
                                qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P842"]: # String
                                qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P843", "P844", "P845"]: # ExternalID
                                qualifiers.add(datatypes.ExternalID(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif isinstance(qual_claim_val, dict) and claim_id == 'P206':
                                for qual_sub_claim_id, qual_sub_claim_val in qual_claim_val.items():
                                    if qual_sub_claim_id in ["P205", "P829"]: # Item
                                        qualifiers.add(datatypes.Item(prop_nr=qual_sub_claim_id, value=qual_sub_claim_val))
                            elif isinstance(qual_claim_val, str) and claim_id in ['P72', 'P840']:
                                if qual_claim_id in ["P812"]: # Item
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif isinstance(qual_claim_val, dict) and claim_id == 'P72':
                                if qual_claim_id in ["P797", "P839"]: # Monolingual Text
                                    qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                                elif qual_claim_id in ["P798"]: # String
                                    qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val['value']))
                            elif isinstance(qual_claim_val, int) and claim_id == 'P72':
                                if qual_claim_id in ["P33"]: # Quantity
                                    qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                            elif isinstance(qual_claim_val, list) and claim_id == 'P72':
                                if qual_claim_id in ["P838"]: # Item
                                    for affiliation in qual_claim_val:
                                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=affiliation[wikibase_name]))
                        print(qualifiers)
                        if 'value' in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict['value'], qualifiers=qualifiers, references=referencesA)
                        elif wikibase_name in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict[wikibase_name], qualifiers=qualifiers, references=referencesA)
                        elif 'P846' in sub_claim_dict:
                            claim_obj = datatypes.Item(prop_nr=claim_id, value=sub_claim_dict['P846'], qualifiers=qualifiers, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
            elif isinstance(claim_dict, dict):
                qualifiers = models.Qualifiers()
                for qual_claim_id, qual_claim_val in claim_dict.items():
                    if qual_claim_id in ["P793", "P794"]: # Time
                        qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY))
                    elif qual_claim_id in ["P492", "P812", "P834", "P835", "P837"]: # Item
                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                if 'value' in claim_dict:
                    claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict['value'], qualifiers=qualifiers, references=referencesA)
                else:
                    print(claim_id)
                    print(claim_dict)
                    claim_obj = datatypes.Item(prop_nr=claim_id, value=claim_dict[wikibase_name], qualifiers=qualifiers, references=referencesA)
            else:
                print("x1")
                print(claim_id)
                print(claim_dict)
                exit()

        elif claim_id in ["P67", "P434", "P830", "P833", "P841"]: # Monolingual Text
            if isinstance(claim_dict, list):
                if isinstance(claim_dict[0], dict):
                    for sub_claim_dict in claim_dict:
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim_dict.items():
                            if qual_claim_id in ["P33"]: # Quantity
                                qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                            elif qual_claim_id in ["P87", "P816", "P826", "P832"]: # Item
                                if qual_claim_val is None:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, snaktype=WikibaseSnakType.NO_VALUE))
                                else:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                            elif qual_claim_id in ["P827", "P831"]: # MonolingualText
                                qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                            elif qual_claim_id in ["P59"]: # Time
                                qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'-00-00'+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR))
                            elif qual_claim_id in ["P450"]: # Item
                                for sub_item in qual_claim_val:
                                    qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=sub_item))
                        claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=sub_claim_dict['value'], language=sub_claim_dict['language'], qualifiers=qualifiers, references=referencesA)
                        item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                        already_appended = True
                elif isinstance(claim_dict[0], list):
                    print(claim_id)
                    if isinstance(claim_dict[0][0], dict):
                        for sub_claim_dict in claim_dict:
                            for infra_claim_dict in sub_claim_dict:
                                qualifiers = models.Qualifiers()
                                for qual_claim_id, qual_claim_val in infra_claim_dict.items():
                                    if qual_claim_id in ["P33"]: # Quantity
                                        qualifiers.add(datatypes.Quantity(prop_nr=qual_claim_id, amount=qual_claim_val))
                                    elif qual_claim_id in ["P87", "P816", "P826", "P832"]:
                                        if qual_claim_val is None:
                                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, snaktype=WikibaseSnakType.NO_VALUE))
                                        else:
                                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                                    elif qual_claim_id in ["P827"]:
                                        qualifiers.add(datatypes.MonolingualText(prop_nr=qual_claim_id, text=qual_claim_val['value'], language=qual_claim_val['language']))
                                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=infra_claim_dict['value'], language=infra_claim_dict['language'], qualifiers=qualifiers, references=referencesA)
                                item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                                already_appended = True
                    else:
                        print("x2")
                        print(claim_id)
                        print(claim_dict)
                        exit()
                else:
                    print("x3")
                    print(claim_id)
                    print(claim_dict)
                    exit()
            elif isinstance(claim_dict, dict):
                claim_obj = datatypes.MonolingualText(prop_nr=claim_id, text=claim_dict['value'], language=claim_dict['language'], references=referencesA)
            else:
                print("x4")
                print(claim_id)
                print(claim_dict)
                exit()

        elif claim_id in ["P3", "P95", "P199"]: # External Identifier
            if claim_id == "P3":
                referencesB = models.references.References()
                referenceB1 = models.references.Reference()
                for ref_id, ref_val in claim_dict['reference'].items():
                    if ref_id in ['P21', 'P278', 'P279']:
                        referenceB1.add(datatypes.Item(prop_nr=ref_id, value=ref_val))
                    elif ref_id in ['P561', 'P562']:
                        referenceB1.add(datatypes.String(prop_nr=ref_id, value=ref_val))
                referencesB.add(referenceB1)
                claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesB)
            else:
                if isinstance(claim_dict, str):
                    claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict, references=referencesA)
                elif isinstance(claim_dict, list):
                    print("x5")
                    print(claim_id)
                    print(claim_dict)
                    exit()
                elif isinstance(claim_dict, dict):
                    qualifiers = models.Qualifiers()
                    for qual_claim_id, qual_claim_val in claim_dict.items():
                        if qual_claim_id in ["P792"]: # String
                            qualifiers.add(datatypes.String(prop_nr=qual_claim_id, value=qual_claim_val))
                        elif qual_claim_id in ["P795"]: # Item
                            qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                    claim_obj = datatypes.ExternalID(prop_nr=claim_id, value=claim_dict['value'], qualifiers=qualifiers, references=referencesA)
                else:
                    print("x6")
                    print(claim_id)
                    print(claim_dict)
                    exit()

        elif claim_id in ["P57", "P76", "P77", "P510", "P511", "P808"]: # String
            if isinstance(claim_dict, str):
                claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict, references=referencesA)
            elif isinstance(claim_dict, list):
                print("x7")
                print(claim_id)
                print(claim_dict)
                exit()
            elif isinstance(claim_dict, dict):
                claim_obj = datatypes.String(prop_nr=claim_id, value=claim_dict['value'], references=referencesA)

        elif claim_id in ["P58", "P469", "P836"]: # Time
            if isinstance(claim_dict, str):
                if claim_dict == "UNKNOWN":
                    claim_obj = datatypes.Time(prop_nr=claim_id, snaktype=WikibaseSnakType.UNKNOWN_VALUE, references=referencesA)
                else:
                    if "-00-00" in str(claim_dict):
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR, references=referencesA)
                    elif "-00" in str(claim_dict):
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.MONTH, references=referencesA)
                    else:
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, references=referencesA)
            elif isinstance(claim_dict, list):
                for sub_claim in claim_dict:
                    
                    if isinstance(sub_claim, dict):
                        qualifiers = models.Qualifiers()
                        for qual_claim_id, qual_claim_val in sub_claim.items():
                            if qual_claim_id in ["P828"]: # Item
                                qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(sub_claim['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, qualifiers=qualifiers, references=referencesA)
                    elif isinstance(sub_claim, str):
                        if sub_claim == "UNKNOWN":
                            claim_obj = datatypes.Time(prop_nr=claim_id, snaktype=WikibaseSnakType.UNKNOWN_VALUE, references=referencesA)
                        else:
                            claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(sub_claim['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, references=referencesA)
                    item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)
                    already_appended = True
            elif isinstance(claim_dict, dict):
                qualifiers = models.Qualifiers()
                for qual_claim_id, qual_claim_val in claim_dict.items():
                    if qual_claim_id in ["P828"]: # Item
                        qualifiers.add(datatypes.Item(prop_nr=qual_claim_id, value=qual_claim_val))
                    elif qual_claim_id in ["P847", "P848"]:
                        qualifiers.add(datatypes.Time(prop_nr=qual_claim_id, time='+'+str(qual_claim_val)+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY))
                if 'precision' in claim_dict:
                    if claim_dict['precision'] == "YEAR":
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.YEAR, qualifiers=qualifiers, references=referencesA)
                    elif claim_dict['precision'] == "MONTH":
                        claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.MONTH, qualifiers=qualifiers, references=referencesA)
                    else:
                        print("Precision value not recognized. Exiting...")
                        exit()
                else:
                    claim_obj = datatypes.Time(prop_nr=claim_id, time='+'+str(claim_dict['value'])+'T00:00:00'+'Z', precision=WikibaseDatePrecision.DAY, qualifiers=qualifiers, references=referencesA)
        else:
            print("x8")
            print(claim_id)
            print(claim_dict)
            print('here2')
            exit()

        if not already_appended:
            item.claims.add(claim_obj, action_if_exists=ActionIfExists.MERGE_REFS_OR_APPEND)

    #print(item)
    item.write()

    exit()

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

def detect_language(str):
    detected_language = detect(str)

    wikibase_lang = None
    for LA, LA_dict in language_json.items():
        if "iso639-1" in LA_dict:
            if LA_dict["iso639-1"] == detected_language:
                punkt = LA_dict["punkt"]
                wikibase_lang = LA_dict["wikibase"]
            elif LA == detected_language:
                punkt = LA_dict["punkt"]
                wikibase_lang = LA_dict["wikibase"]

    return wikibase_lang

def add_to_mapping_file(pubmodel_name):
    new_match = input('What is the QID that matches the publication model "%s"?\n' % (str(pubmodel_name)))
    pubmodel_mappings_json[str(pubmodel_name)][wikibase_name] = new_match.strip()

    with open(constants.PubModel_mapping_file, 'w') as f:
        json.dump(pubmodel_mappings_json, f, indent=4, sort_keys=True)

    return new_match