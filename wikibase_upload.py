#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   wikibase_upload.py
#

from pathlib import Path
from property_matching import return_mappings
from spreadsheet_reader import read_spreadsheet
from wikibaseintegrator import wbi_login, wbi_core, wbi_datatype
from wikibaseintegrator.wbi_config import config as wbi_config

import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

full_bot_name = yaml_dict['wikibase']['full_bot_name']
bot_password = yaml_dict['wikibase']['bot_password']

def main():

    # Replace with your Wikibase login credentials
    login_instance = wbi_login.Login(user=full_bot_name, password=bot_password)
    
    # Specify your file
    file_path = 'your_spreadsheet.xlsx'
    
    # Process and upload the spreadsheet
    process_spreadsheet(file_path, login_instance)

# Preprocess data for Wikibase upload (similar to previous implementation)
def preprocess_row(row, property_mapping):
    data = []
    for column_name, value in row.items():
        if column_name in property_mapping:
            property_id = property_mapping[column_name]
            if property_id == 'P569':  # Date
                data.append(wbi_datatype.Time(value=value, prop_nr=property_id))
            elif property_id == 'P625':  # Coordinate location
                lat, lon = value.split(',')
                data.append(wbi_datatype.GlobeCoordinate(latitude=float(lat), longitude=float(lon), prop_nr=property_id))
            else:
                data.append(wbi_datatype.String(value=value, prop_nr=property_id))
    return data

# Upload to Wikibase
def upload_to_wikibase(row_data, login_instance):
    item = wbi_core.ItemEngine(new_item=True, data=row_data)
    item.write(login_instance)

# Main function to process the spreadsheet (adjusted for property matching)
def process_spreadsheet(file_path, login_instance):
    df = read_spreadsheet(file_path)
    property_mapping = return_mappings(df)
    
    for index, row in df.iterrows():
        row_data = preprocess_row(row, property_mapping)
        upload_to_wikibase(row_data, login_instance)

if __name__ == '__main__':
    main()