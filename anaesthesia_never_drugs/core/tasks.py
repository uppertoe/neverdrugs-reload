from config import celery_app
from django.contrib.postgres.search import SearchVector
from django.db import transaction, OperationalError

from .utils.atc import scrape_atc, scrape_atc_roots
from .models.classifications import AtcImport, WhoAtc
from .models.search import SearchIndex
from .forms.drugs import FORMS_BY_LEVEL

@celery_app.task
def update_search_vector(search_index_pk):
    SearchIndex.objects.filter(pk=search_index_pk).update(
        search_vector=(
            SearchVector('name', weight='A') +
            SearchVector('content', weight='B')
        )
    )

def chunk_generator(generator, chunk_size=20):
    chunk=[]
    for item in generator:
        print(item)
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    # If elements remaining smaller than chunk size
    if chunk:
        yield chunk

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
