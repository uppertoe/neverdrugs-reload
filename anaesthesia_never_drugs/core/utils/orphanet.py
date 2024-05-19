import requests

def get_latest_orphanet_json():
    
    url = 'https://api.orphacode.org/EN/ClinicalEntity'
    headers = {'Apikey': 'test4'}
    
    with requests.get(url, headers=headers) as r:
        
        r.raise_for_status()
        download = r.json()
        
    return download

def unpack_orphanet_json_entry(entry):
    '''Map the JSON fields to the Form fields'''
    output = {'name': entry['Preferred term'],
              'orpha_code': entry['ORPHAcode'],
              'date_updated': entry['Date'],  # Converted to DateTime by the Form
              'description': entry['Definition'],
              'status': entry['Status'],  # Converted to Boolean by the Form
              }
    return output
