from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.apps import apps
import logging

from .models.search import SearchIndex
from .tasks import update_search_vector

from .models.classifications import AtcImport, ChemicalSubstance
from .models.conditions import OrphaEntry, Condition, OrphaImport

'''
Maintain SearchIndex
'''

logger = logging.getLogger(__name__)

# Not called on bulk create/update
def update_or_create_index(sender, instance, **kwargs):
    search_index_instance, _ = SearchIndex.update_or_create_index(instance, search_vector_processed=False)

# Called on bulk delete
def update_search_index_on_delete(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(sender)
    SearchIndex.objects.filter(content_type=content_type, object_id=instance.pk).delete()

# Attach signal to indexed models
for model_label in SearchIndex.INDEXED_MODELS:
    model = apps.get_model(model_label)
    post_save.connect(update_or_create_index, sender=model)
    post_delete.connect(update_search_index_on_delete, sender=model)
    logger.info(f'Connected signals for {model_label}')


'''
Keep Drug up to date with current ChemicalSubstance
'''
# Create or update Drug for each ChemicalSubstance
@receiver(post_save, sender=ChemicalSubstance)
def create_or_update_drug_on_chemical_substance_save(sender, instance, **kwargs):
    # Only proceed if this is the latest AtcImport
    logger.info(f'Considering drug creation for {instance}')
    if instance.atc_import == AtcImport.get_latest_import():
        instance.create_or_update_drug()
        logger.info(f'Drug created: {instance}')


'''
Keep Condition up to date with current OrphaEntry
'''
# Create or update Condition for each OrphaEntry
@receiver(post_save, sender=OrphaEntry)
def create_or_update_condition_on_orpha_entry_save(sender, instance, **kwargs):
    # Only proceed if this is the latest OrphaImport
    if instance.orpha_import == OrphaImport.get_latest_import():
        instance.create_or_update_condition()