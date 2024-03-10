import os
import ijson
import requests
import zipfile
import tempfile
from datetime import datetime
from collections import defaultdict

url = 'https://api.fda.gov/download.json'

def get_latest_json_path(url):
    """
    Fetches the latest JSON file paths for FDA drug data from a given URL.
    
    Parameters:
    - url (str): URL to fetch the download paths from.
    
    Returns:
    - dict: A dictionary containing the parts of the JSON to download and the export date.
    """
    with requests.get(url) as r:
        r.raise_for_status()
        download = r.json()

    drugsfda = download['results']['drug']['drugsfda']  # Gives the URL to the JSON
    exported = drugsfda['export_date']
    
    parts = [url['file'] for url in drugsfda['partitions']]
        
    download_paths = {'parts': parts, 'exported': exported}
    
    return download_paths

def check_export_date(exported):
    """
    Checks if the exported date is more recent than existing data.
    
    Parameters:
    - exported (str): The export date as a string in 'YYYY-MM-DD' format.
    
    Returns:
    - bool: True if the exported date is after the last recorded input, False otherwise.
    """
    exported_date = datetime.strptime(exported, '%Y-%m-%d')
    return exported_date > datetime.today()  # TODO: implement proper check

def stream_file_to_disk(url, directory, filename=None):
    """
    Streams a file from a URL to disk, saving it in the specified directory with an optional filename.
    
    Parameters:
    - url (str): The URL of the file to download.
    - directory (str): The directory where the file should be saved.
    - filename (str, optional): The name of the file. If None, the filename is derived from the URL.
    
    Returns:
    - str: The path to the downloaded file.
    """
    if filename is None:
        filename = url.split('/')[-1]  # Default to the last segment of the URL if no filename is provided
    
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    return path

def unzip_files_to_disk(path):
    """
    Extracts a ZIP file to the same directory where the ZIP file is located.
    
    Parameters:
    - path (str): The path to the ZIP file.
    
    Returns:
    - list: A list of paths to the extracted files.
    """
    directory = os.path.dirname(path)
    extracted_paths = []
    
    with zipfile.ZipFile(path, 'r') as zip_ref:
        names = zip_ref.namelist()
        zip_ref.extractall(directory)
        extracted_paths = [os.path.join(directory, name) for name in names]
    
    return extracted_paths

def stream_process_trade_names(file_path):
    """
    Processes a given JSON file to extract drug names and their trade names.
    
    Parameters:
    - file_path (str): The path to the JSON file.
    
    Returns:
    - defaultdict(set): A dictionary where keys are generic drug names and values are sets of trade names.
    """
    products_dict = defaultdict(set)
    with open(file_path, 'rb') as f:  # Note 'rb' for binary mode, required by ijson
        # Assuming the structure is: {"results": [{"openfda": {"generic_name": [...], "brand_name": [...]}}]}
        for entry in ijson.items(f, 'results.item'):
            if 'openfda' in entry and 'generic_name' in entry['openfda'] and 'brand_name' in entry['openfda']:
                for generic in entry['openfda']['generic_name']:
                    for brand in entry['openfda']['brand_name']:
                        products_dict[generic].add(brand)
    return products_dict

def merge_product_dicts(product_dicts_list):
    """
    Merges a list of product dictionaries into a single dictionary.
    
    Parameters:
    - product_dicts_list (list): A list of dictionaries to merge.
    
    Returns:
    - defaultdict(set): A single dictionary containing all unique generic names and their associated trade names.
    """
    final_products_dict = defaultdict(set)
    for product_dict in product_dicts_list:
        if product_dict:  # Ensure plist is not None
            for generic, brands in product_dict.items():
                final_products_dict[generic].update(brands)
    return final_products_dict

def download_extract_process(download_paths):
    """
    Orchestrates the downloading, extracting, and processing of drug data based on provided paths.
    
    Parameters:
    - download_paths (dict): A dictionary containing the URLs (parts) of the JSON files to download and process.
    
    Returns:
    - defaultdict(set): A dictionary of processed drug names and their trade names.
    """
    if not check_export_date(download_paths['exported']):
        return
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        extracted_files = []
        for part_url in download_paths['parts']:
            zip_path = stream_file_to_disk(part_url, tmpdirname)
            extracted_files.extend(unzip_files_to_disk(zip_path))
            
        product_dicts_list = []
        for file_path in extracted_files:
            if file_path.endswith('.json'):
                product_dicts_list.append(stream_process_trade_names(file_path))
                    
        products = merge_product_dicts(product_dicts_list)
    
    return products
