import dataiku

def do(payload, config, plugin_config, inputs):    

    if payload.get('parameterName') in ['recordId', 'patentId', 'fileId']:
        dataset_name = inputs[0]['fullName']
        dataset = dataiku.Dataset(dataset_name)
        df = dataset.get_dataframe(limit=1)
        cols = list(df.columns)
        choices = [{"value": col, "label": col} for col in cols]
        
        return {"choices": choices}

    return {"choices": []}