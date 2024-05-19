from config import celery_app
from django.contrib.postgres.search import SearchVector
from django.db import transaction, OperationalError

from .utils.atc import scrape_atc, scrape_atc_roots
from .utils.fda import orchestrate_fda_products_download
from .utils.helpers import chunk_queryset, chunk_generator
from .models.classifications import AtcImport, WhoAtc, FdaImport, ChemicalSubstance
from .models.search import SearchIndex
from .forms.drugs import FORMS_BY_LEVEL

'''Search Index'''

@celery_app.task
def update_search_vector(search_index_pk):
    SearchIndex.objects.filter(pk=search_index_pk).update(
        search_vector=(
            SearchVector('name', weight='A') +
            SearchVector('content', weight='B')
        )
    )


'''WHO ATC scraping'''

@celery_app.task(time_limit=60*60*2, soft_time_limit=59*60*2)
def import_who_atc():
    # Create new AtcImport
    atc_import_instance = AtcImport.objects.create(active=False)
    atc_roots_dict = scrape_atc_roots()
    
    for root, root_name in atc_roots_dict.items():
        # scrape_atc should be run serially
        for chunk in chunk_generator(scrape_atc(root)):
            # Each chunk is created as a separate process
            chunk_task = process_atc_chunk.s(chunk, atc_import_instance.pk, root_name)
            chunk_task.apply_async()


@celery_app.task(autoretry_for=(OperationalError,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def process_atc_chunk(chunk, atc_import_pk, root_name):
    atc_import_instance = AtcImport.objects.get(pk=atc_import_pk)
    errors = []

    with transaction.atomic():  # Prevent race condition between Celery workers
        for entry in chunk:
            # Find the correct form for this level in the hierarchy
            level = entry['level']
            FormClass = FORMS_BY_LEVEL.get(level)
            
            if FormClass:
                # Overwrite an existing instance if it exists
                AtcModel = WhoAtc.get_model_by_level(level)
                code = entry['code']
                entry_instance_queryset = AtcModel.objects.filter(code=code, atc_import=atc_import_instance).select_for_update()
                entry_instance = entry_instance_queryset.first()

                # Instantiate the form
                form = FormClass(
                    entry,
                    instance=entry_instance,  # Overwrite instance if exists
                    atc_import_instance=atc_import_instance,
                    root_name=root_name,  # Ensure ATC root parents are named
                    )
                
                if form.is_valid():
                    form.save()
                    atc_import_instance.increment_element_inserted_count()
                else:
                    errors.extend(form.errors)
    
    return errors


'''Drug model updating'''
@celery_app.task()
def process_drug_chunk(chemical_substance_ids):
    for chemical_substance_id in chemical_substance_ids:
        try:
            chemical_substance = ChemicalSubstance.objects.get(id=chemical_substance_id)
            chemical_substance.create_or_update_drug()
        except ChemicalSubstance.DoesNotExist:
            continue

@celery_app.task(retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def dispatch_update_drug_objects(atc_import_pk, chunk_size=100):
    atc_import = AtcImport.objects.get(pk=atc_import_pk)
    drugs_to_update = ChemicalSubstance.objects.filter(atc_import=atc_import)

    for chunk in chunk_queryset(drugs_to_update, chunk_size):
        process_drug_chunk.delay(chunk)



'''FDA drug aliases'''

# Create an FdaImport
# Receive a dictionary in the form generic:{brands,}
# Chunk the results for batch processing
# Filter Drugs by the generic name
# If a brand does not exist, create a DrugAlias
# Increment FdaImport.drug_alises_imported

@celery_app.task()
def import_fda_aliases():
    fda_import = FdaImport.objects.create()
    products_dict = orchestrate_fda_products_download()  # Approx 15 seconds

    # Drug names have already been filtered

