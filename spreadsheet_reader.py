#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   spreadsheet_reader.py
#

from pathlib import Path

import pandas as pd
import yaml

# Read in YAML file.
yaml_dict=yaml.safe_load(Path("project.yaml").read_text())

def main():
    spreadsheet_file_name = yaml_dict['spreadsheet']['spreadsheet_name']
    spreadsheet_df = read_spreadsheet(spreadsheet_file_name, header=1, skiprows=3)

def read_spreadsheet(file_path, header=1, skiprows=0):
    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path, header=header, skiprows=skiprows)
    elif file_path.endswith('.xls'):
        df = pd.read_excel(file_path, header=header, skiprows=skiprows)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path, header=header, skiprows=skiprows)
    elif file_path.endswith('.tsv'):
        df = pd.read_csv(file_path, sep='\t', header=header, skiprows=skiprows)
    else:
        raise ValueError('Unsupported file format. Use Excel, CSV, or TSV.')
    return df

if __name__ == '__main__':
    main()