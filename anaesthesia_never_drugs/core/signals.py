from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.apps import apps

from .models.search import SearchIndex
from .tasks import update_search_vector


# Not called on bulk create/update
def update_or_create_index(sender, instance, **kwargs):
    search_index_instance, _ = SearchIndex.get_or_create_index(instance)
    update_search_vector.delay(search_index_instance.pk)

# Called on bulk delete
def update_search_index_on_delete(sender, instance, **kwargs):
    content_type = ContentType.objects.get_for_model(sender)
    SearchIndex.objects.filter(content_type=content_type, object_id=instance.pk).delete()

# Attach signal to indexed models
for model_label in SearchIndex.INDEXED_MODELS:
    model = apps.get_model(model_label)
    post_save.connect(update_or_create_index, sender=model)
    post_delete.connect(update_search_index_on_delete, sender=model)