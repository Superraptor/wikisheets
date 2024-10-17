#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_date.py
#

def process_date(pubmed_date):
    if 'Year' in pubmed_date:
        year = pubmed_date['Year']
        month = pubmed_date.get('Month', '01')
        day = pubmed_date.get('Day', '01')
        return f"{year}-{month}-{day}"
    return None