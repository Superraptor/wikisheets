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
    get_wikidata_id("33015654")

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

    if isinstance(identifier, str):
        identifier = [identifier]

    if os.path.isfile(file_name):
        with open(file_name, 'r') as f:
            id_dict = json.load(f)

    to_find_list = []
    found_dict = {}
    for iden in identifier:
        if iden not in id_dict.keys():
            to_find_list.append(iden)
        else:
            found_dict[iden] = id_dict[iden]

    if len(to_find_list) > 0:

        formatted_identifier = " ".join([f'"{iden}"' for iden in to_find_list])

        # Set up the appropriate SPARQL query depending on the identifier type
        if id_type == "PubMed":
            query = f"""
            SELECT ?otherID ?wikidataID WHERE {{
            ?wikidataID wdt:P698 ?otherID .
            VALUES ?otherID {{ {formatted_identifier} }}.
            }}
            """
        elif id_type == "NLM":
            query = f"""
            SELECT ?otherID ?wikidataID WHERE {{
            ?wikidataID wdt:P1055 ?otherID .
            VALUES ?otherID {{ {formatted_identifier} }}.
            }}
            """
        elif id_type == "ORCID":
            query = f"""
            SELECT ?otherID ?wikidataID WHERE {{
            ?wikidataID wdt:P496 ?otherID .
            VALUES ?otherID {{ {formatted_identifier} }}.
            }}
            """
        else:
            raise ValueError("id_type must be 'PubMed', 'NLM', or 'ORCID'.")
        
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
                results = response.json()["results"]["bindings"]
                for result in results:
                    id_dict[result["otherID"]["value"]] = (result['wikidataID']['value']).rsplit('/', 1)[-1]
                    found_dict[result["otherID"]["value"]] = (result['wikidataID']['value']).rsplit('/', 1)[-1]
                with open(file_name, 'w') as f:
                    json.dump(id_dict, f, indent=4, sort_keys=True)
                if len(to_find_list) == 1:
                    return found_dict[to_find_list[0]]
                else:
                    return found_dict
            else:
                for iden in to_find_list:
                    id_dict[iden] = None
                with open(file_name, 'w') as f:
                    json.dump(id_dict, f, indent=4, sort_keys=True)
                if len(to_find_list) > 1:
                    return found_dict
                else:
                    return None
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")

    else:
        if len(identifier) == 1:
            return found_dict[identifier[0]]
        else:
            return found_dict

# Example usage:
# wikidata_id = get_wikidata_id("27679979", id_type="PubMed")
# print(wikidata_id)

if __name__ == '__main__':
    main()