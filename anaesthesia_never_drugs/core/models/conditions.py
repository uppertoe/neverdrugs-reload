from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.core.cache import cache

# Implementation of Orphanet clinical entities database

class OrphaImport(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    element_count = models.PositiveIntegerField(default=0)
    elements_inserted = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)

    @classmethod
    def get_latest_import(cls):
        # Cached as may be frequently called with bulk updates
        cache_key = f'{cls.__name__}_get_latest_import'
        result = cache.get(cache_key)

        if result is None:
            result = cls.objects.filter(active=True).order_by('-timestamp').first()
            if result:
                cache.set(cache_key, result, 60*5)  # Cache for 5 minutes
        
        return result
    
    @classmethod
    def invalidate_get_latest_import_cache(cls):
        cache_key = f'{cls.__name__}_get_latest_import' 
        cache.delete(cache_key)
    
    def increment_element_inserted_count(self):
        self.elements_inserted = F('elements_inserted')+1
        self.save()

    def trigger_condition_updates(self):
        # Update Condition objects associated with this OrphaImport
        from ..tasks import dispatch_update_condition_objects
        dispatch_update_condition_objects.delay(self.pk)
    
    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure either both or neither operations proceed
            if self.active:  # Ensure only 1 active
                OrphaImport.objects.exclude(pk=self.pk).update(active=False)
                self.trigger_condition_updates()
            self.invalidate_get_latest_import_cache()
            super().save(*args, **kwargs)

    def __str__(self):
        local_timestamp = self.timestamp.astimezone(timezone.get_current_timezone())
        return local_timestamp.strftime('%d-%m-%Y %T')
    

class OrphaEntry(models.Model):
    name = models.CharField(max_length=255)
    orpha_code = models.CharField(max_length=15)
    description = models.CharField(max_length=2048, null=True, blank=True)
    orpha_import = models.ForeignKey(OrphaImport, on_delete=models.CASCADE)
    date_updated = models.DateTimeField()
    status = models.CharField(max_length=255)

    def create_or_update_condition(self):
        defaults = {'name': self.name,
                    'description': self.description,
                    'date_updated': self.date_updated,
                    'status': self.status,}
        condition, created = Condition.objects.update_or_create(
            orpha_code=self.orpha_code,
            defaults=defaults
        )

        return condition, created

    def __str__(self):
        return self.name


class Condition(models.Model):
    name = models.CharField(max_length=255)
    orpha_code = models.CharField(max_length=15, unique=True)
    description = models.CharField(max_length=2048, null=True, blank=True)
    date_updated = models.DateTimeField()
    status = models.CharField(max_length=255)
    orpha_category = models.ManyToManyField('OrphaCategory', through='ConditionOrphaCategory')

    def __str__(self):
        return self.name


class ConditionSynonym(models.Model):
    name = models.CharField(max_length=255)
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE, related_name='synonyms')


class ConditionOrphaCategory(models.Model):
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    orpha_category = models.ForeignKey('OrphaCategory', on_delete=models.CASCADE)


class OrphaCategory(models.Model):
    name = models.CharField(max_length=255)


