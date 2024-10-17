#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   pubmed_format.py
#

from pubmed_format_article import process_article
from pubmed_format_grant import process_grant
from pubmed_format_journal import process_journal

# This file is intended to map the Entrez output format
# (https://www.nlm.nih.gov/bsd/mms/medlineelements.html)
# to a Wikibase instance.

def process_object(entrez_obj):
    journal_id = process_journal(entrez_obj)
    article_id = process_article(entrez_obj, journal_id)


    


    

