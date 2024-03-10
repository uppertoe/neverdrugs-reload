from config import celery_app
from celery import group
from django.contrib.postgres.search import SearchVector

from .utils.atc import ATC_ROOTS, scrape_atc, scrape_atc_roots
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

def chunk_generator(generator, chunk_size=50):
    chunk=[]
    for item in generator:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    # If elements remaining smaller than chunk size
    if chunk:
        yield chunk

@celery_app.task
def import_who_atc():
    # Create new AtcImport
    atc_import_instance = AtcImport.objects.create(active=False)
    chunk_tasks = []
    atc_roots_dict = scrape_atc_roots()

    for root, root_name in atc_roots_dict.items():
        # scrape_atc should be run serially
        for chunk in chunk_generator(scrape_atc(root)):
            # Each chunk is created as a separate process
            chunk_task = process_atc_chunk.s(chunk, atc_import_instance.pk, root_name)
            chunk_tasks.append(chunk_task)

    # Collected data may be processed in parallel
    task_group = group(chunk_tasks)
    result = task_group.apply_async()

    return result

@celery_app.task
def process_atc_chunk(chunk, atc_import_pk, root_name):
    atc_import_instance = AtcImport.objects.get(pk=atc_import_pk)
    errors = []
    for entry in chunk:
        # Find the correct form for this level in the hierarchy
        level = entry['level']
        FormClass = FORMS_BY_LEVEL.get(level)
        
        if FormClass:
            # Overwrite an existing instance if it exists
            AtcModel = WhoAtc.get_model_by_level(level)
            try:
                code = entry['code']
                entry_instance = AtcModel.objects.get(code=code, atc_import=atc_import_instance)
            except AtcModel.DoesNotExist:
                entry_instance = None

            # Instantiate the form
            form = FormClass(
                entry,
                atc_import_instance=atc_import_instance,
                instance=entry_instance,
                root_name=root_name,  # Ensure ATC root parents are named
                )
            
            if form.is_valid():
                form.save()
                atc_import_instance.increment_element_inserted_count()
            else:
                errors.extend(form.errors)
    
    return errors
