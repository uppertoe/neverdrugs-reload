from django.db import models
from django.contrib.postgres.search import SearchVectorField, SearchQuery
from django.contrib.postgres.indexes import GinIndex
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class SearchIndex(models.Model):
    # Indexed models should implement get_search_index_data
    INDEXED_MODELS = {'core.ChemicalSubstance', 'core.Drug', 'core.DrugAlias'}

    name = models.CharField(max_length=255)
    content = models.TextField(null=True, blank=True)
    search_vector = SearchVectorField(null=True)
    updated_at = models.DateTimeField(auto_now=True)
    model_name = models.CharField(max_length=255, null=True, blank=True)  # For convenience
    searchable = models.BooleanField(default=False)

    # Related object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        indexes = [GinIndex(fields=['search_vector'])]
        verbose_name_plural = "search indices"

    @classmethod
    def update_or_create_index(cls, related_object):        
        content_type = ContentType.objects.get_for_model(related_object)
        object_id = related_object.id

        # Dynamically get the fields dictionary from the related object
        # Calls lambda: {} if get_search_index_data method does not exist
        index_data = getattr(related_object, 'get_search_index_data', lambda: {})()

        # Prepare the data for updating or creating the SearchIndex entry
        update_fields = {
            'name': index_data.get('name', str(related_object)),
            'content': index_data.get('content', ''),
            'model_name': f"{content_type.app_label}.{content_type.model}",
            'searchable': index_data.get('searchable', False),
        }

        search_index, created = cls.objects.update_or_create(
            content_type=content_type,
            object_id=object_id,
            defaults=update_fields
        )

        return search_index, created
    
    @staticmethod
    def get_content_type(instance):
        return ContentType.objects.get_for_model(instance)

    @staticmethod
    def search(query):
        search_query = SearchQuery(query, config='english')
        results = SearchIndex.objects.filter(search_vector=search_query)
        return results

    def __str__(self):
        return f'{self.model_name} - {self.object_id}'