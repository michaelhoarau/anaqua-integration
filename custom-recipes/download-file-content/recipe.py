# -*- coding: utf-8 -*-
import dataiku

from dataiku.customrecipe import get_input_names_for_role
from dataiku.customrecipe import get_output_names_for_role
from anaquaintegration.utils import run_initialization
from anaquaintegration.wrappers import download_document

# Initialization:
init          = run_initialization()
mode          = init['config'].get("mode", "ALL")
record_id_col = init['config'].get("fileId", None)
verbose_mode  = init['verboseMode']
BASE_URL      = init['baseUrl']
KEY_ID        = init['keyId']
KEY_SECRET    = init['keySecret']
logger        = init['logger']

if not "record_id_col":
    raise ValueError("Missing required recipe parameter: you must select the column that contains the file ID")

# Datasets:
input_names = get_input_names_for_role('input_dataset')
documents_dataset = dataiku.Dataset(input_names[0])
output_names = get_output_names_for_role('output_dataset')
output_folder = dataiku.Folder(output_names[0])
documents_df = documents_dataset.get_dataframe(columns=[record_id_col, 'PatentId', 'FileName'])

# Loops through all the documents to download their content:
for index, raw in documents_df.iterrows():
    download_document(BASE_URL, KEY_ID, KEY_SECRET, raw, output_folder)
    
    if (index + 1) % 10 == 0:
        logger.info("********** ---[ Anaqua Download Document Content Recipe ]--- **********")
        logger.info(f"{index + 1} documents downloaded")