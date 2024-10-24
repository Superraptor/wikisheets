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

    download_pubmed_metadata(args.q, max_results=10)

# Step 1: Query PubMed and download metadata
def download_pubmed_metadata(keyword, mesh=True, max_results=100, use_existing_pmids=True):
    print(f"Searching PubMed for articles related to: {keyword}")
    
    # Search PubMed with the keyword or MeSH term or something else
    if mesh:
        keyword = ('"%s"' % keyword) + '[MeSH]'
    else:
        keyword = ('"%s"' % keyword) + '[OT]'
    handle = Entrez.esearch(db="pubmed", term=keyword, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    
    pubmed_ids = record["IdList"]
    
    print(f"Found {len(pubmed_ids)} articles. Fetching metadata...")
    file_json = {}
    #filtered_keyword = ((keyword.replace(' ', '_')).replace('"','')).replace("'", "")
    #file_name = f"pubmed_{filtered_keyword}_{str(max_results)}.json"
    #if os.path.isfile(file_name):
    #    with open(file_name, 'r') as f:
    #        file_json = json.load(f)
    #else:
    #    file_json = {}

    #setA = set(pubmed_ids)
    #setB = set(file_json.keys())

    #pubmed_ids = setA.difference(setB)

    # Fetch article details using the list of PubMed IDs
    if len(pubmed_ids) > 0:
        handle = Entrez.efetch(db="pubmed", id=",".join(pubmed_ids), retmode="xml")
        records = Entrez.read(handle)
        handle.close()
    #elif use_existing_pmids:
    #    records = {}
    #    records["PubmedArticle"] = []
    #    with open(file_name, 'r') as f:
    #        json_data = json.load(f)
    #        for pmid, article in json_data.items():
    #            records["PubmedArticle"].append({
    #                "MedlineCitation": article
    #            })

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

    exit()
    
    # Create DataFrame and save it as a spreadsheet
    df = pd.DataFrame(articles)
    file_name = f"pubmed_{filtered_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(file_name, index=False)
    
    print(f"Saved metadata to {file_name}")
    return file_name

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