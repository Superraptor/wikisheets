#!/usr/bin/env python

#
#   Clair Kronk
#   15 October 2024
#   pubmed_format_space_flight_mission.py
#

import constants
import json

with open(constants.SFM_mapping_file, 'r') as f:
    space_flight_mission_json = json.load(f)

# SFM: Space Flight Mission
def process_space_flight_mission():
    print()