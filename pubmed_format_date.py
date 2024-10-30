#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_date.py
#

from daterangeparser import parse
from time import strptime

import pyparsing

def process_date(pubmed_date):
    if 'Year' in pubmed_date:
        year = pubmed_date['Year']
        if 'Month' in pubmed_date:
            try:
                month = strptime(str(pubmed_date['Month']), '%b').tm_mon
            except ValueError:
                month = str(pubmed_date['Month'])
            if len(str(month)) == 1:
                month = "0" + str(month)
            if 'Day' in pubmed_date:
                day = pubmed_date['Day']
                if len(str(day)) == 1:
                    day = "0" + str(day)
                return f"{year}-{month}-{day}"
            else:
                return f"{year}-{month}-00"
        else:
            return f"{year}-00-00"
    return None

def process_date_range(pubmed_date):
    try:
        earliest_date, latest_date = parse(str(pubmed_date))
    except pyparsing.exceptions.ParseException:
        pubmed_date_array = str(pubmed_date).split()
        pubmed_date_array.reverse()
        new_pubmed_date = " ".join(pubmed_date_array)
        earliest_date, latest_date = parse(str(new_pubmed_date))

    if earliest_date.year == latest_date.year and earliest_date.month == latest_date.month:
        shared_overlap = str(f"{earliest_date.year}-{earliest_date.month:02d}") + "-00"
        precision_val = "MONTH"
    
    # Check if they share the same year
    elif earliest_date.year == latest_date.year:
        shared_overlap = str(f"{earliest_date.year}") + "-00-00"
        precision_val = "YEAR"
    
    # If neither, return an appropriate message
    else:
        print("The PubMed date range (%s) does not appear to share a year or month." % str(pubmed_date))
        exit()

    return {
        'value': shared_overlap,
        'P847': str(f"{earliest_date.year}-{earliest_date.month:02d}-{earliest_date.day:02d}"),
        'P848': str(f"{latest_date.year}-{latest_date.month:02d}-{latest_date.day:02d}"),
        'precision': precision_val
    }