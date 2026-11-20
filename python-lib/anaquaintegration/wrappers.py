import dataiku
import json
import os
import tempfile

from anaquaintegration.utils import aqx_request

def get_transaction_id(BASE_URL, KEY_ID, KEY_SECRET, logger):
    # Get last transaction ID:
    API_PATH = "/api/v11.2/Synchronization/CurrentSynchronizationTransactionId"
    response = aqx_request(
        method="GET",
        base_url=BASE_URL,
        api_path=API_PATH,
        api_key_id=KEY_ID,
        api_key_content=KEY_SECRET
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to retrieve current Anaqua transaction ID. "
            f"Endpoint: {API_PATH}."
            f"Status code: {response.status_code}."
        )

    raw_text = response.text.strip()
    try:
        last_transaction_id = int(raw_text.strip('"'))
    except (ValueError, TypeError):
        raise RuntimeError(
            f"Unexpected response when retrieving current transaction ID. "
            f"Expected integer, got: {raw_text[:200]}"
        )

    logger.debug("********** ---[ Anaqua Read Inventions Recipe ]--- **********")
    logger.debug(f"Last transaction ID collected: {last_transaction_id}")
    
    return last_transaction_id

def get_result_id(BASE_URL, KEY_ID, KEY_SECRET, logger, start_transaction_id, last_transaction_id):
    # First, we need to run a search and get a result id:
    payload = {
      "StartingTransactionId": start_transaction_id,
      "EndingTransactionId": last_transaction_id,
      "RecordTypes": [
        "Invention"
      ]
    }
    
    # Search for all transaction changes up until that transaction id. This
    # extracts all the changes since day 1, that a given account has access
    # to. This might be quite slow, so finding a proper "StartingTransactionId"
    # based on dates would probably be valuable (TODO)
    API_PATH = "/api/v11.2/MatterSynchronizationRecordInfo/RecordChanges"
    response = aqx_request(
        method="POST",
        base_url=BASE_URL,
        api_path=API_PATH,
        api_key_id=KEY_ID,
        api_key_content=KEY_SECRET,
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to search for inventions via RecordChanges."
            f"Endpoint: {API_PATH}."
            f"Status code: {response.status_code}."
        )

    try:
        resp_json = response.json()
    except:
        try:
            resp_json = json.loads(response.text)
        except Exception as e:
            body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
            raise RuntimeError(
                f"RecordChanges returned a non-JSON response. "
                f"Endpoint: {API_PATH}. "
                f"Body excerpt: {body_excerpt}"
            ) from e

    if not isinstance(resp_json, dict):
        raise RuntimeError(
            f"Unexpected RecordChanges response type. Expected JSON object, got {type(resp_json).__name__}."
        )

    result_id = resp_json.get("ResultId")
    if not result_id or not isinstance(result_id, int):
        raise RuntimeError(
            f"RecordChanges response missing/invalid 'ResultId'. "
            f"Keys present: {sorted(resp_json.keys())[:30]}"
        )

    logger.debug("********** ---[ Anaqua Read Inventions Recipe ]--- **********")
    logger.debug("Payload to search for all transaction changes:")
    logger.debug(payload)
    logger.debug("Results:")
    logger.debug(resp_json)
    
    return result_id

def get_inventions_list(BASE_URL, KEY_ID, KEY_SECRET, logger, result_id):
    # Now we have a result id, we loop through all the results associated to it:
    page_number = 1
    num_results = 1
    num_inventions = 0
    inventions_list = []
    logger.info("********** ---[ Anaqua Read Inventions Recipe ]--- **********")
    while num_results > 0:
        API_PATH = f"/api/v11.2/MatterSynchronizationRecordInfo/RecordChangeResults?resultId={result_id}&pageNumber={page_number}&pageSize=50"
        response = aqx_request(
            method="GET",
            base_url=BASE_URL,
            api_path=API_PATH,
            api_key_id=KEY_ID,
            api_key_content=KEY_SECRET
        )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to search for inventions list. "
                f"Endpoint: {API_PATH}. "
                f"Status code: {response.status_code}."
            )
            
        try:
            resp_json = response.json()
        except:
            try:
                resp_json = json.loads(response.text)
            except Exception as e:
                body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
                raise RuntimeError(
                    f"RecordChangeResults returned a non-JSON response. "
                    f"Endpoint: {API_PATH}. "
                    f"Body excerpt: {body_excerpt}"
                ) from e
                
        if not isinstance(resp_json, list):
            raise RuntimeError(
                f"Unexpected RecordChangeResults response type. Expected JSON list, got {type(resp_json).__name__}."
            )
            
        if not all(isinstance(item, dict) for item in resp_json):
            bad_types = {type(item).__name__ for item in resp_json if not isinstance(item, dict)}
            raise RuntimeError(
                f"Unexpected RecordChangeResults response element types. Expected list of dicts, got non-dict types: {sorted(bad_types)}."
            )

        current_inventions_list = resp_json
        num_results = len(current_inventions_list)
        num_inventions += num_results

        if num_results > 0:
            inventions_list += current_inventions_list
            logger.info(f"{num_inventions} inventions extracted")
            page_number += 1
            
    return inventions_list

def get_inventions_metadata(BASE_URL, KEY_ID, KEY_SECRET, logger, inventions_list):
    for index, inv in enumerate(inventions_list):
        invention_id = inv['RecordId']
        
        logger.debug("********** ---[ Anaqua Read Inventions Metadata ]--- **********")
        logger.debug(f'- Processing invention {invention_id}')
        
        API_PATH = f"/api/v11.2/InventionMatterSynchronizationInfo/{invention_id}"
        response = aqx_request(
            method="GET",
            base_url=BASE_URL,
            api_path=API_PATH,
            api_key_id=KEY_ID,
            api_key_content=KEY_SECRET
        )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to search for inventions metadata. "
                f"Endpoint: {API_PATH}. "
                f"Status code: {response.status_code}."
            )
            
        try:
            resp_json = response.json()
        except:
            try:
                resp_json = json.loads(response.text)
            except Exception as e:
                body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
                raise RuntimeError(
                    f"InventionMatter returned a non-JSON response. "
                    f"Endpoint: {API_PATH}. "
                    f"Body excerpt: {body_excerpt}"
                ) from e
                
        inventions_list[index] = {**inventions_list[index], **response.json()}
        
    return inventions_list

def get_patents_list(BASE_URL, KEY_ID, KEY_SECRET, logger, input_dataset_name, record_id_col):
    inventions_dataset = dataiku.Dataset(input_dataset_name)
    inventions_list = list(inventions_dataset.get_dataframe(columns=[record_id_col])[record_id_col])

    logger.debug("********** ---[ Anaqua Read Patents Recipe ]--- **********")
    logger.debug(f"{len(inventions_list)} invention(s) found in the input dataset")

    patents = []
    for invention_id in inventions_list:
        API_PATH = f"/api/v11.2/PatentMatterSynchronizationInfo/PatentFamily?inventionId={invention_id}"
        response = aqx_request(
            method="GET",
            base_url=BASE_URL,
            api_path=API_PATH,
            api_key_id=KEY_ID,
            api_key_content=KEY_SECRET
        )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to search for patents linked to invention {invention_id}. "
                f"Endpoint: {API_PATH}. "
                f"Status code: {response.status_code}."
            )
            
        try:
            resp_json = response.json()
        except:
            try:
                resp_json = json.loads(response.text)
            except Exception as e:
                body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
                raise RuntimeError(
                    f"PatentFamily returned a non-JSON response. "
                    f"Endpoint: {API_PATH}. "
                    f"Body excerpt: {body_excerpt}"
                ) from e
                
        if not isinstance(resp_json, list):
            raise RuntimeError(
                f"Unexpected PatentFamily response type. Expected JSON list, got {type(resp_json).__name__}."
            )
            
        if not all(isinstance(item, dict) for item in resp_json):
            bad_types = {type(item).__name__ for item in resp_json if not isinstance(item, dict)}
            raise RuntimeError(
                f"Unexpected PatentFamily response element types. Expected list of dicts, got non-dict types: {sorted(bad_types)}."
            )

        if len(resp_json) > 0:
            patents += resp_json

            logger.debug("********** ---[ Anaqua Read Patents Recipe ]--- **********")
            logger.debug(f"- {len(resp_json)} patent(s) found for invention {invention_id}")
            
    return patents

def get_documents_metadata(BASE_URL, KEY_ID, KEY_SECRET, logger, input_dataset_name, record_id_col):
    patents_dataset = dataiku.Dataset(input_dataset_name)
    patents_list = list(patents_dataset.get_dataframe()[record_id_col])
    documents = []
    for patent_id in patents_list:
        logger.debug("********** ---[ Anaqua Read Document Metadata Recipe ]--- **********")
        logger.debug("Processing patent #{patent_id}:")

        API_PATH = f"/api/v11.2/DocumentSynchronizationRecordFileLinkInfo/RecordFileLinksInfo?recordId={patent_id}"
        response = aqx_request(
            method="GET",
            base_url=BASE_URL,
            api_path=API_PATH,
            api_key_id=KEY_ID,
            api_key_content=KEY_SECRET
        )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to search for files linked to patent {patent_id}. "
                f"Endpoint: {API_PATH}. "
                f"Status code: {response.status_code}."
            )
            
        try:
            resp_json = response.json()
        except:
            try:
                resp_json = json.loads(response.text)
            except Exception as e:
                body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
                raise RuntimeError(
                    f"RecordFileLinksInfo returned a non-JSON response. "
                    f"Endpoint: {API_PATH}. "
                    f"Body excerpt: {body_excerpt}"
                ) from e
                
        if not isinstance(resp_json, list):
            raise RuntimeError(
                f"Unexpected RecordFileLinksInfo response type. Expected JSON list, got {type(resp_json).__name__}."
            )
            
        if not all(isinstance(item, dict) for item in resp_json):
            bad_types = {type(item).__name__ for item in resp_json if not isinstance(item, dict)}
            raise RuntimeError(
                f"Unexpected RecordFileLinksInfo response element types. Expected list of dicts, got non-dict types: {sorted(bad_types)}."
            )

        if len(resp_json) > 0:
            logger.debug("********** ---[ Anaqua Read Document Metadata Recipe ]--- **********")
            logger.debug(f"{len(resp_json)} documents found for this patent")

            docs = []
            for doc in resp_json:
                fileId = doc['FileId']
                API_PATH = f"/api/v11.2/DocumentSynchronizationFile/DocumentSynchronizationInfo?fileId={fileId}"
                response = aqx_request(
                    method="GET",
                    base_url=BASE_URL,
                    api_path=API_PATH,
                    api_key_id=KEY_ID,
                    api_key_content=KEY_SECRET
                )
                
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Failed to search for metadata linked to file {fileId}. "
                        f"Endpoint: {API_PATH}. "
                        f"Status code: {response.status_code}."
                    )
                
                try:
                    file_json = response.json()
                except:
                    try:
                        file_json = json.loads(response.text)
                    except Exception as e:
                        body_excerpt = (response.text or "").replace("\n", " ").replace("\r", " ")[:600]
                        raise RuntimeError(
                            f"DocumentSynchronizationInfo returned a non-JSON response. "
                            f"Endpoint: {API_PATH}. "
                            f"Body excerpt: {body_excerpt}"
                        ) from e

                if not isinstance(file_json, dict):
                    raise RuntimeError(
                        f"Unexpected DocumentSynchronizationInfo response type. Expected JSON dict, got {type(resp_json).__name__}."
                    )

                file_json['RecordId'] = doc['RecordId']
                docs.append(file_json)

            documents += docs
            
    return documents

def download_document(BASE_URL, KEY_ID, KEY_SECRET, fileProperties, targetFolder):
    filename = fileProperties['FileName']
    patent = fileProperties['PatentId']
    fileId = fileProperties['FileId']

    API_PATH = f"/api/v11.2/DocumentSynchronizationFile/{fileId}"
    response = aqx_request(
        method="GET",
        base_url=BASE_URL,
        api_path=API_PATH,
        api_key_id=KEY_ID,
        api_key_content=KEY_SECRET
    )
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to search for content linked to file {fileId}. "
            f"Endpoint: {API_PATH}. "
            f"Status code: {response.status_code}."
        )
        
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) == 0:
                raise RuntimeError(f"Downloaded file {file_id} has Content-Length=0.")
        except ValueError:
            # Ignore malformed Content-Length but continue to the next file
            pass

    if not response.content:
        raise RuntimeError(f"Downloaded file {file_id} is empty (no content).")

    # Write atomically to avoid corrupted files and delete the local file once upload is done:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        target_path = f"{patent}/{filename}"
        targetFolder.upload_file(target_path, tmp_path)
    finally:
        os.remove(tmp_path)