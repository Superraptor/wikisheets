#!/usr/bin/env python

#
#   Clair Kronk
#   2 October 2024
#   url_processing.py
#

from datatype_matching import detect_url
from waybackpy import WaybackMachineCDXServerAPI, WaybackMachineSaveAPI

import datetime
import requests

def main():
    get_url_info("https://www.google.com/", "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")

def get_url_info(text, user_agent):
    is_url=detect_url(text, public=False, accessible=False)
    is_public_url=detect_url(text, public=True, accessible=False)
    is_accessible=detect_url(text, public=False, accessible=True)
    status_code = get_status_code(text)

    if status_code != 200:
        print() # Add inaccessible here.

    url_archive=get_archived_url(text, user_agent)
    
    url_object = {
        "url": text,
        "is_url": is_url,
        "public": is_public_url,
        "accessible": is_accessible,
        "status_code": status_code,
        "archive": url_archive
    }

    return url_object

def get_status_code(text):
    try:
        r = requests.head(text)
    except requests.ConnectionError:
        print("Failed to connect. Exiting...")
        exit()

def get_archived_url(text, user_agent):

    found=False

    # Get nearest archive from current Unix timestamp.
    cdx_api = WaybackMachineCDXServerAPI(text, user_agent)
    timestamp = datetime.datetime.now().timestamp()
    archived_url = cdx_api.near(unix_timestamp=timestamp)
    print(archived_url)
    print(archived_url.statuscode)

    # Test if it works.
    if archived_url.statuscode != str(200):
        # If it does not work try oldest.
        archived_url = cdx_api.oldest()
        print(archived_url)
        print(archived_url.statuscode)
        if archived_url.statuscode == str(200):
            found=True
    else:
        found=True

    # If not found and validated save new version.
    if found is False:
        save_api = WaybackMachineSaveAPI(text, user_agent)
        archived_url = save_api.save()
        return {
            "url": archived_url,
            "timestamp": save_api.timestamp()
        }
    else:
        return {
            "url": archived_url.archive_url,
            "timestamp": archived_url.timestamp,
            "datetime": archived_url.datetime_timestamp,
            "status_code": archived_url.statuscode,
            "mimetype": archived_url.mimetype
        }

if __name__ == '__main__':
    main()