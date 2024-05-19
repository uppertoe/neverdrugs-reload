from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.core.cache import cache

# Implementation of the Anatomical Therapeutic Chemical (ATC) Classification System

class AtcImport(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    element_count = models.PositiveIntegerField(default=0)
    elements_inserted = models.PositiveIntegerField(default=0)
    drugs_inserted = models.PositiveIntegerField(default=0)
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

    def trigger_drug_updates(self):
        # Update Drug objects associated with this AtcImport
        from ..tasks import dispatch_update_drug_objects
        dispatch_update_drug_objects.delay(self.pk)
    
    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure either both or neither operations proceed
            if self.active:  # Ensure only 1 active AtcImport
                AtcImport.objects.exclude(pk=self.pk).update(active=False)
                self.trigger_drug_updates()
            self.invalidate_get_latest_import_cache()
            super().save(*args, **kwargs)

    def __str__(self):
        local_timestamp = self.timestamp.astimezone(timezone.get_current_timezone())
        return local_timestamp.strftime('%d-%m-%Y %T')


class FdaImport(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    drug_aliases_inserted = models.IntegerField(default=0)

    def increment_drug_aliases_inserted(self):
        # Use an F query to avoid race conditions
        pass


class WhoAtc(models.Model):
    name = models.CharField(max_length=255, null=True)
    code = models.CharField(max_length=7, db_index=True)
    atc_import = models.ForeignKey(AtcImport, on_delete=models.CASCADE, related_name="%(class)ss")
    searchable = models.BooleanField(default=True)

    def get_search_index_data(self):
        return {'name': self.name,
                'content': '',
                'searchable': self.searchable}
    
    @staticmethod
    def get_model_by_level(level):
        '''Returns a model corresponding to a level in the ATC hierarchy'''
        models = {1: AnatomicalMainGroup,
                  2: TherapeuticMainGroup,
                  3: TherapeuticPharmacologicalSubgroup,
                  4: ChemicalTherapeuticPharmacologicalSubgroup,
                  5: ChemicalSubstance,
                  }
        return models.get(level)
    
    def __str__(self):
        return f'{self.code}: {self.name}'

    class Meta:
        abstract = True


class AnatomicalMainGroup(WhoAtc):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'atc_import'], name='unique_anatomical_main_group')
        ]


class TherapeuticMainGroup(WhoAtc):
    parent = models.ForeignKey(AnatomicalMainGroup, on_delete=models.CASCADE, null=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'atc_import'], name='unique_therapeutic_main_group')
        ]

class TherapeuticPharmacologicalSubgroup(WhoAtc):
    parent = models.ForeignKey(TherapeuticMainGroup, on_delete=models.CASCADE, null=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'atc_import'], name='unique_therapeutic_pharmacological_subgroup')
        ]

class ChemicalTherapeuticPharmacologicalSubgroup(WhoAtc):
    parent = models.ForeignKey(TherapeuticPharmacologicalSubgroup, on_delete=models.CASCADE, null=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'atc_import'], name='unique_chemical_therapeutic_pharmacological_subgroup')
        ]

class ChemicalSubstance(WhoAtc):
    parent = models.ForeignKey(ChemicalTherapeuticPharmacologicalSubgroup, on_delete=models.CASCADE, null=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'atc_import'], name='unique_chemical_substance')
        ]

    @classmethod
    def create_drug_batches(cls, batch_size=50):
        queryset = cls.objects.all()
        total = queryset.count()

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            yield queryset[start:end]

    def create_or_update_drug(self):
        from .drugs import Drug

        # Filter by name (case insensitive)
        drugs = Drug.objects.filter(name__iexact=self.name.lower())

        # Account for multiple matches
        if drugs.exists():
            for drug in drugs:
                # Add current category
                drug.atc_category.add(self)
        else:
            # Create a new drug if none exists
            drug = Drug.objects.create(name=self.name)
            drug.atc_category.add(self)

