from config import celery_app
from celery import chord
from django.contrib.postgres.search import SearchVector
from django.db import transaction, OperationalError
import logging

from .utils.atc import scrape_atc, scrape_atc_roots
from .utils.fda import orchestrate_fda_products_download
from .utils.orphanet import get_latest_orphanet_json, unpack_orphanet_json_entry
from .utils.helpers import chunk_queryset, chunk_generator, iterable_batch_generator
from .models.classifications import AtcImport, WhoAtc, FdaImport, ChemicalSubstance
from .models.conditions import OrphaImport, Condition, OrphaEntry
from .models.search import SearchIndex
from .forms.drugs import FORMS_BY_LEVEL
from .forms.conditions import OrphaEntryForm

logger = logging.getLogger(__name__)

'''Search Index'''

@celery_app.task()
def update_search_vector(search_index_pks):
    # Calculate the SearchVector for a given SearchIndex object
    for search_index_pk in search_index_pks:
        SearchIndex.objects.filter(pk=search_index_pk).update(
            search_vector=(
                SearchVector('name', weight='A') +
                SearchVector('content', weight='B')
            ),
            search_vector_processed=True,
        )

@celery_app.task()
def dispatch_search_vector_updates(result):
    # Log results of chained process
    batch_count = len(result)
    processed = sum(result)
    logger.info(f'{batch_count} batches for {processed} objects updated')

    objects_to_process = SearchIndex.objects.filter(search_vector_processed=False)
    ids = list(objects_to_process.values_list('id', flat=True))
    batches = iterable_batch_generator(ids, batch_size=100)

    for batch in batches:
        update_search_vector.delay(batch)


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
    processed_count = 0
    for chemical_substance_id in chemical_substance_ids:
        try:
            chemical_substance = ChemicalSubstance.objects.get(pk=chemical_substance_id)
            logging.info(f'Chemical substance being processed: {chemical_substance}')
            chemical_substance.create_or_update_drug()
            processed_count += 1
        except ChemicalSubstance.DoesNotExist:
            continue
    return processed_count  # Signal completion to the Chord

@celery_app.task(retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def dispatch_update_drug_objects(atc_import_pk, batch_size=100):
    atc_import = AtcImport.objects.get(pk=atc_import_pk)
    drugs_to_update = ChemicalSubstance.objects.filter(atc_import=atc_import)

    # Create child tasks consisting of drugs to update
    ids = list(drugs_to_update.values_list('id', flat=True))  # Evaluate queryset to prevent race conditions
    batches = iterable_batch_generator(ids, batch_size)
    child_tasks = [process_drug_chunk.s(batch) for batch in batches]

    # Use a Chord to trigger the SearchIndex update once child tasks are complete
    chord(child_tasks)(dispatch_search_vector_updates.s())

'''Orphanet'''

@celery_app.task()
def process_orphanet_batch(batch, orpha_import_pk):
    errors = []

    # Get current OrphaImport
    orpha_import_instance = OrphaImport.objects.get(pk=orpha_import_pk)

    # Iterate over the batch
    for condition in batch:
        form = OrphaEntryForm(
            unpack_orphanet_json_entry(condition),
            orpha_import_instance=orpha_import_instance,
        )

        if form.is_valid():
            form.save()
            orpha_import_instance.increment_element_inserted_count()
        else:
            errors.extend(form.errors)
    
    return errors

@celery_app.task(autoretry_for=(OperationalError,), retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def dispatch_orphanet_imports():
    # Download the latest JSON
    orphanet_json = get_latest_orphanet_json()
    
    # Record the target number of entries
    element_count = len(orphanet_json)

    # Create a new OrphaImport
    orpha_import = OrphaImport.objects.create(active=False, element_count=element_count)

    # Create the batches
    for batch in iterable_batch_generator(orphanet_json, batch_size=50):
        process_orphanet_batch.delay(batch, orpha_import.pk)
        
'''Condition model updating'''
@celery_app.task()
def process_condition_chunk(orpha_entry_ids):
    processed_count = 0
    for orpha_entry_id in orpha_entry_ids:
        try:
            orpha_entry = OrphaEntry.objects.get(id=orpha_entry_id)
            orpha_entry.create_or_update_condition()
            processed_count += 1
        except OrphaEntry.DoesNotExist:
            continue
    return processed_count  # Signal completion to the Chord

@celery_app.task(retry_kwargs={'max_retries': 5, 'countdown': 60}, retry_backoff=True)
def dispatch_update_condition_objects(orpha_import_pk, batch_size=100):
    orpha_import = OrphaImport.objects.get(pk=orpha_import_pk)
    conditions_to_update = OrphaEntry.objects.filter(orpha_import=orpha_import)

    # Create child tasks consisting of drugs to update
    ids = list(conditions_to_update.values_list('id', flat=True))  # Evaluate queryset to prevent race conditions
    batches = iterable_batch_generator(ids, batch_size)
    child_tasks = [process_condition_chunk.s(batch) for batch in batches]

    # Use a Chord to trigger the SearchIndex update once child tasks are complete
    chord(child_tasks)(dispatch_search_vector_updates.s())

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

