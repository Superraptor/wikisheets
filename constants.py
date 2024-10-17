#
#   PUBMED MAPPINGS
#

# Primary Mappings

AD_mapping_file = "pubmed-affiliation-mappings.json"

AU_mapping_file = "pubmed-authors.json"

# Grant institutes/organizations based on:
# https://wayback.archive-it.org/org-350/20210414192512/https://www.nlm.nih.gov/bsd/grant_acronym.html
GR_mapping_file = "pubmed-grant-codes.json"

# Countries based on:
# https://www.ncbi.nlm.nih.gov/genbank/collab/country/
PL_mapping_file = "pubmed-countries.json"

# Map language based on:
# https://www.nlm.nih.gov/bsd/language_table.html
LA_mapping_file = "pubmed-language-mappings.json"

MH_mapping_file = "pubmed-mesh-headings.json"

OT_mapping_file = "pubmed-keywords.json"

# Publication types based on:
# https://pubmed.ncbi.nlm.nih.gov/help/#publication-types
# https://www.nlm.nih.gov/mesh/pubtypes.html
PT_mapping_file = "pubmed-publication-types.json"

# Subsets based on:
# https://www.nlm.nih.gov/bsd/mms/medlineelements.html#sb
SB_mapping_file = "pubmed-citation-subset.json"

# Space flight missions based on:
# https://wayback.archive-it.org/org-350/20200416183254/https://www.nlm.nih.gov/bsd/space_flight.html
SFM_mapping_file = "pubmed-space-flight-mission.json"

# Secondary Mappings

# NLM category based on:
# https://www.nlm.nih.gov/bsd/policy/structured_abstracts.html
NlmCategory_mapping_file = "pubmed-nlmcategory.json"

# Tertiary Mappings
grants_mapping_file = "pubmed-grants.json"
nlm_wikibase_mapping_file = "nlm-wikibase-mapping.json"
pmid_wikibase_mapping_file = "pmid-wikibase-mapping.json"

#
#   SPARQL QUERIES
#

PROPERTIES_LABEL_QUERY = """PREFIX wd: <https://lgbtdb.wikibase.cloud/entity/>
PREFIX wdt: <https://lgbtdb.wikibase.cloud/prop/direct/>

SELECT DISTINCT ?property ?propertyLabel ?propertyDescription ?propertyAltLabel ?datatype WHERE {
  # Retrieve properties
  ?property a wikibase:Property.
  
  # Get property label and description
  OPTIONAL { ?property rdfs:label ?propertyLabel. FILTER(LANG(?propertyLabel) = "en") }
  OPTIONAL { ?property schema:description ?propertyDescription. FILTER(LANG(?propertyDescription) = "en") }

  # Get property aliases
  OPTIONAL { ?property skos:altLabel ?propertyAltLabel. FILTER(LANG(?propertyAltLabel) = "en") }
  
  # Get the datatype of the property
  OPTIONAL { ?property wikibase:propertyType ?datatype. }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

PROPERTY_VALUES_QUERY = """PREFIX wd: <https://lgbtdb.wikibase.cloud/entity/>
PREFIX wdt: <https://lgbtdb.wikibase.cloud/prop/direct/>

SELECT DISTINCT ?x ?z WHERE {
    ?x wdt:%s ?z.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT 20"""

WIKIDATA_MAPPING_QUERY = """PREFIX wd: <https://lgbtdb.wikibase.cloud/entity/>
PREFIX wdt: <https://lgbtdb.wikibase.cloud/prop/direct/>

SELECT DISTINCT ?x WHERE {
    ?x wdt:%s '%s'.
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT 1"""

# Currently written with values from Wikidata; needs replacement
# values for use with Wikibase.
PROPERTIES_MATRIX_QUERY = """PREFIX wd: <https://lgbtdb.wikibase.cloud/entity/>
PREFIX wdt: <https://lgbtdb.wikibase.cloud/prop/direct/>

SELECT DISTINCT ?property ?propertyLabel ?propertyDescription ?propertyAltLabel ?datatype ?subjectType ?valueType ?rangeConstraint ?integerConstraint ?formatConstraint ?wikidata WHERE {
  # Retrieve properties
  ?property a wikibase:Property.
  
  # Get property label and description
  OPTIONAL { ?property rdfs:label ?propertyLabel. FILTER(LANG(?propertyLabel) = "en") }
  OPTIONAL { ?property schema:description ?propertyDescription. FILTER(LANG(?propertyDescription) = "en") }

  # Get property aliases
  OPTIONAL { ?property skos:altLabel ?propertyAltLabel. FILTER(LANG(?propertyAltLabel) = "en") }
  
  # Get the datatype of the property
  OPTIONAL { ?property wikibase:propertyType ?datatype. }

  # Get subject-type constraint if any
  OPTIONAL { 
    ?property p:P2302 ?constraintStatement.
    ?constraintStatement ps:P2302 wd:Q21503250;  # subject type constraint
                        pq:P2308 ?subjectType.
  }
  
  # Get value-type constraint if any
  OPTIONAL { 
    ?property p:P2302 ?constraintStatement2.
    ?constraintStatement2 ps:P2302 wd:Q21510865;  # value type constraint
                         pq:P2309 ?valueType.
  }

  # Get range constraint if any
  OPTIONAL { 
    ?property p:P2302 ?constraintStatement3.
    ?constraintStatement3 ps:P2302 wd:Q21510860;  # range constraint
                         pq:P2313 ?rangeConstraint.
  }
  
  # Get integer constraint if any
  OPTIONAL { 
    ?property p:P2302 ?constraintStatement4.
    ?constraintStatement4 ps:P2302 wd:Q52848401.  # integer constraint
  }

  # Get format constraint if any
  OPTIONAL { 
    ?property p:P2302 ?constraintStatement5.
    ?constraintStatement5 ps:P2302 wd:Q21502404.  # format constraint
  }

  # Get Wikidata mapping of any
  OPTIONAL { ?property wdt:%s ?wikidata. }
  
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""