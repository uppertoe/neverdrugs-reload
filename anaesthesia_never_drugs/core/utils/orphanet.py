import requests

def get_latest_json():
    
    url = 'https://api.orphacode.org/EN/ClinicalEntity'
    headers = {'Apikey': 'test4'}
    
    with requests.get(url, headers=headers) as r:
        
        r.raise_for_status()
        download = r.json()
        
    return download

