#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   datatype_matching.py
#

from urllib.parse import urlparse

import socket
import validators

def main():
    print()

# Commons media file

# EDTF Date/Time

# Entity Schema

# External identifier

# Form

# Geographic coordinates

# Geographic shape

# Item

# Lexeme

# Mathematical expression

# Monolingual text

# Musical Notation

# Point in time

# Property

# Quantity
    # amount: decimal
    # lowerBound: decimal
    # upperBound: decimal
    # unit: IRI or "1" to indicate the unit "unit"

# Sense

# String

# Tabular data

# URL
def detect_url(text, public=True, accessible=True):

    # Test if a URL is public.
    if public:
        validation = validators.url(text, public=True)
    else:
        validation = validators.url(text)

    # Test if a URL is currently accessible.
    if accessible:
        if is_connected():
            result = urlparse(text)
            if result.scheme and result.netloc:
                validation = True
            else:
                validation = False
        else:
            print("Accessibility cannot be tested as you are not connected to the internet. Reconnect and try again. Exiting...")
            exit()

    if validation:
        return True
    else:
        return False
    
def is_connected(hostname="one.one.one.one"):
    try:
        host=socket.gethostbyname(hostname)
        s=socket.create_connection((host,80),2)
        s.close()
        return True
    except Exception:
        pass
    return False

if __name__ == '__main__':
    main()