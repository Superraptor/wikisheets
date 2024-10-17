#!/usr/bin/env python

#
#   Clair Kronk
#   4 October 2024
#   wikidata_mapping.py
#

import json
import os.path
import requests

def main():
    print()

# TODO: Generalize.
def get_wikidata_id(identifier, id_type="PubMed"):
    """
    Retrieves the Wikidata ID given a PubMed ID or NLM Unique ID.
    
    Args:
        identifier (str): The PubMed ID or NLM Unique ID.
        id_type (str): The type of identifier. Either "PubMed" or "NLM". Default is "PubMed".
        
    Returns:
        str: The Wikidata ID if found, otherwise None.
    """

    id_dict = {}
    file_name = None

    if id_type == "PubMed":
        file_name = "pubmed-wikidata-mapping.json"
    elif id_type == "NLM":
        file_name = "nlm-wikidata-mapping.json"
    elif id_type == "ORCID":
        file_name = "orcid-wikidata-mapping.json"
    else:
        print("id_type must be 'PubMed' or 'NLM'. Exiting...")
        exit()

    if os.path.isfile(file_name):
        with open(file_name, 'r') as f:
            id_dict = json.load(f)

    print(identifier)
    if identifier not in id_dict.keys():

        # Set up the appropriate SPARQL query depending on the identifier type
        if id_type == "PubMed":
            query = f"""
            SELECT ?wikidataID WHERE {{
            ?wikidataID wdt:P698 "{identifier}".
            }}
            """
        elif id_type == "NLM":
            query = f"""
            SELECT ?wikidataID WHERE {{
            ?wikidataID wdt:P1055 "{identifier}".
            }}
            """
        elif id_type == "ORCID":
            query = f"""
            SELECT ?wikidataID WHERE {{
            ?wikidataID wdt:P496 "{identifier}".
            }}
            """
        else:
            raise ValueError("id_type must be either 'PubMed' or 'NLM'.")
        
        # Set up the SPARQL endpoint URL
        url = 'https://query.wikidata.org/sparql'
        headers = {'Accept': 'application/sparql-results+json'}
        params = {'query': query}
        
        # Make the HTTP GET request
        response = requests.get(url, headers=headers, params=params)
        
        # Check if the response is OK
        if response.status_code == 200:
            data = response.json()
            if data['results']['bindings']:
                id_dict[identifier] = ((data['results']['bindings'][0]['wikidataID']['value']).rsplit('/'))[1]
                with open(file_name, 'w') as f:
                    json.dump(id_dict, f)
                return data['results']['bindings'][0]['wikidataID']['value']
            else:
                id_dict[identifier] = None
                with open(file_name, 'w') as f:
                    json.dump(id_dict, f)
                return None
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")

    else:
        return id_dict[identifier]

# Example usage:
# wikidata_id = get_wikidata_id("27679979", id_type="PubMed")
# print(wikidata_id)

if __name__ == '__main__':
    main()