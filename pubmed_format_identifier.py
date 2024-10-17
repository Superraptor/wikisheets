#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_identifier.py
#

def process_elocation_ids(elocation_id_array):
    processed_ids = {}

    eidtype = None
    eidvalid = None
    sourceval = None

    for elocation_id in elocation_id_array:
        eidval = str(elocation_id)
        try:
            if 'EIdType' in elocation_id.attributes:
                eidtype = str(elocation_id.attributes['EIdType'])
            if 'ValidYN' in elocation_id.attributes:
                eidvalid = 'Q23075' if str(elocation_id.attributes['ValidYN']) == 'Y' else 'Q26205'
            if 'Source' in elocation_id.attributes:
                sourceval = str(elocation_id.attributes['Source'])
        except AttributeError:
            pass

        if eidtype:
            if eidtype == 'doi':
                processed_ids['P95'] = process_doi(str(eidval), str(eidvalid))
            elif eidtype == 'pii':
                processed_ids['P808'] = process_pii(str(eidval), str(eidvalid))
            else:
                print("ElocationID (%s) of type %s not recognized. Exiting..." % (str(eidval), str(eidtype)))
                exit()
        else:
            pass

    return processed_ids

# ['Article']['ELocationID']
def process_doi(eidval, eidvalid):
    return {
        'value': eidval,
        'P795': eidvalid
    }

# ['Article']['ELocationID']
def process_pii(eidval, eidvalid):
    return {
        'value': eidval,
        'P795': eidvalid
    }

# ['Article']['Journal']['ISSN']
def process_issn(issn_element):
    issn = str(issn_element)
    issn_obj = {}
    try:
        issn_type = 'P433' if str(issn_element.attributes['IssnType']) == 'Electronic' else 'P432'
        issn_obj[issn_type] = issn
    except AttributeError:
        issn_obj['P430'] = { 'value': issn }
    return issn_obj

# ['Article']['AuthorList'][0]['Identifier']
def process_orcid():
    print()

# ['PMID']
def process_pmid(pmid_element):
    pmid = str(pmid_element)
    pmid_obj = {'value': pmid}
    try:
        version = str(pmid_element.attributes['Version'])
        pmid_obj['P792'] = version
    except AttributeError:
        pass
    return pmid_obj