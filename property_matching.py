#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   property_matching.py
#

from spreadsheet_reader import read_spreadsheet
from wikibase_properties import get_wikibase_properties

import re
import spacy

# Load the SpaCy NER model
nlp = spacy.load("en_core_web_sm")

def main():
    spreadsheet_df = read_spreadsheet('qrh-coverage.xls', header=1, skiprows=3)
    wikibase_properties = get_wikibase_properties()
    inferred_mappings = return_mappings(spreadsheet_df, wikibase_properties, include_user_input=False)
    print(inferred_mappings)

def return_mappings(df, wikibase_properties, include_user_input=False):

    # Dictionary to hold inferred mappings
    inferred_mappings = {}

    for column_name in df.columns:
        # Step 1: NER-based entity recognition on column name
        doc = nlp(column_name)
        entity_type = None
        for ent in doc.ents:
            entity_type = ent.label_
            break

        # Step 2: Datatype inference based on column values
        sample_value = df[column_name].dropna().iloc[0] if not df[column_name].dropna().empty else ''
        inferred_datatype = infer_datatype(sample_value)

        # Step 3: Match entity type and datatype to Wikibase properties
        matched_property = match_property(entity_type, inferred_datatype, wikibase_properties)

        # Store the inferred mapping
        inferred_mappings[column_name] = matched_property

    return inferred_mappings

# Helper function to infer datatype
def infer_datatype(value):
    # Basic datatype inference using regex and other heuristics
    if isinstance(value, str):
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            return 'time'  # Date in the format YYYY-MM-DD
        elif re.match(r'^-?\d+(\.\d+)?$', value):
            return 'number'  # Could be latitude or longitude
        else:
            return 'string'
    elif isinstance(value, (int, float)):
        return 'number'
    return 'string'

# Helper function to match the inferred entity type and datatype to Wikibase properties
def match_property(entity_type, inferred_datatype, properties):
    # Simplistic matching logic: You can refine this based on your actual property list
    if entity_type in ['PERSON', 'ORG']:
        return 'P31'  # Instance of (this could be extended for person-related properties)
    elif entity_type == 'DATE' or inferred_datatype == 'time':
        return 'P569'  # Date of birth or similar properties
    elif entity_type == 'GPE' or inferred_datatype == 'globe-coordinate':
        return 'P625'  # Coordinate location
    else:
        # Fallback to a default string property if nothing matches
        return 'P373'  # Commons category as an example
    # You can add more rules for matching specific entity types to other properties

if __name__ == '__main__':
    main()