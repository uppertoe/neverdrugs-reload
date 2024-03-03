import requests
import re
import time
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urlparse, parse_qs

from . import filters

# Scrape the Anatomical Therapeutic Chemical Classification

atc_roots = ('A', 'B', 'C', 'D', 'G', 'H', 'J', 'L', 'M', 'N', 'P', 'R', 'S', 'V')

# Initialise a session to re-use TCP connections
session = requests.Session()
crawl_delay = 1

def scrape_atc(atc_code):
    '''
    Given an ATC root code, recursively scrapes this root
    Yields a dictionary per entry in each level of the hierarchy processed
    '''
    # Check the current recursion level
    atc_levels = {1: 1, 3: 2, 4: 3, 5: 4, 7: 5}  # len(atc_code):level
    level = atc_levels.get(len(atc_code))
    
    if not level:
        print(f'Error: Incorrect ATC code length {atc_code}')
        return  # Using return here to end the generator
    
    if level == 5:
        return  # Stop recursion for level 5
    
    web_address = f'https://atcddd.fhi.no/atc_ddd_index/?code={atc_code}&showdescription=no'
    response = session.get(web_address)
    # Implement crawl delay
    time.sleep(crawl_delay)
    
    only_id_content = SoupStrainer(id='content')
    soup = BeautifulSoup(response.content, 'lxml', parse_only=only_id_content)
    links = soup.find_all('a')[level+2:]
    links = links[:-1] if level == 4 else links  # Adjust for level 4 formatting
    
    for link in links:
        parsed_url = urlparse(link['href'])
        query_params = parse_qs(parsed_url.query)
        child_atc_code = query_params.get('code', [None])[0]
        
        if child_atc_code and len(child_atc_code) > len(atc_code):  # Recursion stops
            child_level = atc_levels.get(len(child_atc_code))
            link_text = link.get_text(strip=True)  # Ensure names are properly capitalized and stripped
            child_dict = {
                'code': child_atc_code,
                'level': child_level,
                'parent': atc_code,
                'name': link_text
            }
            
            yield child_dict  # Yielding each child dictionary as it's processed
            
            # Recursively yield from child ATC codes
            yield from scrape_atc(child_atc_code)

# Filter the results

def split_by_multiple_delimiters(text, delimiters):
    '''
    Uses a regex to split text by a delimiter in a list of strings
    Returns a list of strings
    '''
    # Create a regular expression pattern from the delimiters
    # The pattern will look something like: 'delimiter1|delimiter2|...'
    pattern = '|'.join(map(re.escape, delimiters))
    
    # Split the text by the compiled pattern
    result = re.split(pattern, text, flags=re.IGNORECASE)
    
    return result

def process_drug_name(names):
    '''
    For each input string, split using multiple delimiters
    Then remove strings corresponding with the supplied blacklist
    Returns a list of strings
    '''
    # Convert blacklist items to lowercase for case-insensitive comparison
    blacklist = [item.lower() for item in filters.blacklist]
    
    # Split into individual drug names
    split_text = split_by_multiple_delimiters(names, filters.delimiters)
    
    # Filter resulting strings
    filtered_names = []
    for drug in split_text:
        # Remove patterns with exactly one space before "(" and the entire "(...)"
        drug_cleaned = re.sub(r' \([^)]*\)', '', drug).strip()
        
        # Check blacklist
        if drug_cleaned.lower() not in blacklist:
            filtered_names.append(drug_cleaned)
    
    return filtered_names