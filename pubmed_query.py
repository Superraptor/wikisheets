#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   pubmed_query.py
#

from Bio import Entrez
from datetime import datetime
from pathlib import Path

import argparse
import json
import os.path
import pandas as pd
import pubmed_format
import time
import wikidata_mapping
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

# PubMed email (provide a valid email address)
Entrez.email = yaml_dict['entrez']['entrez_email']

def main():

    # Parse arguments
    parser=argparse.ArgumentParser()
    parser.add_argument('-q', type=str, required=False, help='The query string to search using.')
    args=parser.parse_args()

    download_pubmed_metadata(args.q)

# Step 1: Query PubMed and download metadata
def download_pubmed_metadata(keyword, mesh=True, retmax=100, use_existing_pmids=True):
    print(f"Searching PubMed for articles related to: {keyword}")
    
    # Search PubMed with the keyword or MeSH term or something else
    if mesh:
        keyword = ('"%s"' % keyword) + '[MeSH]'
    else:
        keyword = ('"%s"' % keyword) + '[OT]'

    pubmed_ids = []
    retstart = 0

    while True:
        handle = Entrez.esearch(db="pubmed", term=keyword, retmax=retmax, retstart=retstart)
        record = Entrez.read(handle)
        handle.close()

        ids = record['IdList']
        pubmed_ids.extend(ids)

        if len(ids) < retmax:
            break
    
        retstart += retmax
    
    print(f"Found {len(pubmed_ids)} articles. Fetching metadata...")
    file_json = {}

    final_pubmed_ids = []
    pubmed_wikibase_mappings = {}
    with open('pmid-wikibase-mapping.json', 'r') as f:
        pubmed_wikibase_mappings = json.load(f)

    for pubmed_id in pubmed_ids:
        if pubmed_id not in pubmed_wikibase_mappings.keys():
            final_pubmed_ids.append(pubmed_id)

    # Fetch article details using the list of PubMed IDs
    if len(final_pubmed_ids) > 0:
    #    if len(final_pubmed_ids) > 500:
    #        chunks = [final_pubmed_ids[x:x+100] for x in range(0, len(final_pubmed_ids), 100)]
    #    else:
    #        chunks = [final_pubmed_ids]
    #
    #    for counter, chunk in enumerate(chunks):
    #        print("Obtaining Wikidata identifiers for chunk %s out of %s..." % (str(counter), str(len(chunks))))
    #        wikidata_mapping.get_wikidata_id(chunk, id_type="PubMed")
    #        time.sleep(10)

        handle = Entrez.efetch(db="pubmed", id=",".join(final_pubmed_ids), retmode="xml")
        records = Entrez.read(handle)
        handle.close()

    # Extract metadata
    to_add = []
    for article in records["PubmedArticle"]:
        if 'PMID' in article["MedlineCitation"]:
            if 'PMID' not in file_json.keys():
                file_json[article["MedlineCitation"]['PMID']] = article["MedlineCitation"]
                #with open(file_name, 'w') as f:
                #    json.dump(file_json, f)

        print(article["MedlineCitation"])

        pubmed_objects = pubmed_format.process_object(article["MedlineCitation"])
        to_add.append(pubmed_objects)

def format_pub_date(pub_date):
    """Convert PubMed's complex date format to a simple 'YYYY-MM-DD' string."""
    if 'Year' in pub_date:
        year = pub_date['Year']
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')
        return f"{year}-{month}-{day}"
    return "Unknown"

if __name__ == '__main__':
    main()