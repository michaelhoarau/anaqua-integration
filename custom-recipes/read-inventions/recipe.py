# -*- coding: utf-8 -*-
import dataiku
import logging
import pandas as pd

from dataiku.customrecipe import get_output_names_for_role
from anaquaintegration.utils import run_initialization
from anaquaintegration.wrappers import get_transaction_id, get_result_ids, get_inventions_list, get_inventions_metadata

# Initialization:
init         = run_initialization()
mode         = init['config'].get("mode", "ALL")
verbose_mode = init['verboseMode']
BASE_URL     = init['baseUrl']
KEY_ID       = init['keyId']
KEY_SECRET   = init['keySecret']
logger       = init['logger']

# Derive the start transaction id depending
# on the current mode selected by the user:
if mode == "ALL":
    start_transaction_id = 0
elif mode == "NEW":
    # TO DO: how do we persist the last transaction id from a given run?
    start_transaction_id = 0
    
last_transaction_id = get_transaction_id(BASE_URL, KEY_ID, KEY_SECRET, logger)
result_ids          = get_result_ids(BASE_URL, KEY_ID, KEY_SECRET, logger, start_transaction_id, last_transaction_id)

# To get the inventions list, we load the last transaction id,
# run a search for all record changes of type "Inventions" with
# that transaction id and then loops through the paginated results:
inventions_list     = get_inventions_list(BASE_URL, KEY_ID, KEY_SECRET, logger, result_ids)
#inventions_list     = get_inventions_metadata(BASE_URL, KEY_ID, KEY_SECRET, logger, inventions_list)

# Write recipe outputs:
inventions_list_df = pd.DataFrame(inventions_list)
#inventions_list_df['TransactionId'] = int(last_transaction_id)
output_names = get_output_names_for_role('output_dataset')
inventions_dataset = dataiku.Dataset(output_names[0])
inventions_dataset.write_with_schema(inventions_list_df)