
class UnsupportedAtcLevelException(Exception):
    '''ATC levels < 2 or > 5 should not be encountered by the WHO ATC scraper'''
    pass