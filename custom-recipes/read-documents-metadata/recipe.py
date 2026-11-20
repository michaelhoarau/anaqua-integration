# -*- coding: utf-8 -*-
import dataiku
import pandas as pd

from dataiku.customrecipe import get_input_names_for_role
from dataiku.customrecipe import get_output_names_for_role
from anaquaintegration.utils import run_initialization
from anaquaintegration.wrappers import get_documents_metadata

# Initialization:
init          = run_initialization()
mode          = init['config'].get("mode", "ALL")
record_id_col = init['config'].get("patentId", None)
verbose_mode  = init['verboseMode']
BASE_URL      = init['baseUrl']
KEY_ID        = init['keyId']
KEY_SECRET    = init['keySecret']
logger        = init['logger']

if not "record_id_col":
    raise ValueError("Missing required recipe parameter: you must select the column that contains the patent record ID")

# Looping through the patents to collect
# the associated documents and their metadatas:
input_names = get_input_names_for_role('input_dataset')
documents = get_documents_metadata(BASE_URL, KEY_ID, KEY_SECRET, logger, input_names[0], record_id_col)

# Write recipe outputs
documents_df = pd.DataFrame(documents)
documents_df = documents_df.rename(columns={"RecordId": "PatentId"})
output_names = get_output_names_for_role('output_dataset')
documents_dataset = dataiku.Dataset(output_names[0])
documents_dataset.write_with_schema(documents_df)