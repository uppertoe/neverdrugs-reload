import pandas as pd

from config import celery_app

@celery_app.task()
def process_fda_drugs(file):
    pass