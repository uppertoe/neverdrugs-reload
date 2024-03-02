import requests
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urlparse, parse_qs

atc_roots = ('A', 'B', 'C', 'D', 'G', 'H', 'J', 'L', 'M', 'N', 'P', 'R', 'S', 'V')

def scrape_atc(atc_code):
    '''
    Scrapes the WHO Anatomical Therapeutic Chemical Classification
    Available at https://atcddd.fhi.no/atc_ddd_index/
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
    response = requests.get(web_address)
    
    only_id_content = SoupStrainer(id='content')
    soup = BeautifulSoup(response.content, 'lxml', parse_only=only_id_content)
    links = soup.find_all('a')[level+2:]
    links = links[:-1] if level == 4 else links  # Adjust for level 4 formatting
    
    for link in links:
        parsed_url = urlparse(link['href'])
        query_params = parse_qs(parsed_url.query)
        child_atc_code = query_params.get('code', [None])[0]
        
        if child_atc_code:  # Ensure child_atc_code is not None
            child_level = atc_levels.get(len(child_atc_code))
            link_text = link.get_text(strip=True).capitalize()  # Ensure names are properly capitalized and stripped
            child_dict = {
                'code': child_atc_code,
                'level': child_level,
                'parent': atc_code,
                'name': link_text
            }
            
            yield child_dict  # Yielding each child dictionary as it's processed
            
            # Recursively yield from child ATC codes
            yield from scrape_atc(child_atc_code)
