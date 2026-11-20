# -*- coding: utf-8 -*-
import dataiku
import pandas as pd

from dataiku.customrecipe import get_input_names_for_role
from dataiku.customrecipe import get_output_names_for_role
from anaquaintegration.utils import run_initialization
from anaquaintegration.wrappers import get_patents_list

# Initialization:
init          = run_initialization()
mode          = init['config'].get("mode", "ALL")
record_id_col = init['config'].get("recordId", None)
verbose_mode  = init['verboseMode']
BASE_URL      = init['baseUrl']
KEY_ID        = init['keyId']
KEY_SECRET    = init['keySecret']
logger        = init['logger']

if not "record_id_col":
    raise ValueError("Missing required recipe parameter: you must select the column that contains the invention record ID")

# Looping through the inventions to collect
# the patent families associated to them:
input_names = get_input_names_for_role('input_dataset')
patents = get_patents_list(BASE_URL, KEY_ID, KEY_SECRET, logger, input_names[0], record_id_col)

# Write recipe outputs
output_names = get_output_names_for_role('output_dataset')
patents_dataset = dataiku.Dataset(output_names[0])
patents_df = pd.DataFrame(patents)
patents_dataset.write_with_schema(patents_df)