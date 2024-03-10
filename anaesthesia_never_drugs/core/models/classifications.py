from django.db import models, transaction
from django.db.models import F


# Implementation of the Anatomical Therapeutic Chemical (ATC) Classification System

class AtcImport(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    element_count = models.PositiveIntegerField(default=0)
    elements_inserted = models.PositiveIntegerField(default=0)
    drugs_inserted = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)

    @classmethod
    def get_latest_import(cls):
        return cls.objects.filter(active=True).order_by('-timestamp').first()
    
    def increment_element_inserted_count(self):
        self.update(elements_inserted=F('elements_inserted')+1)
    
    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensure either both or neither operations proceed
            if self.active:  # Ensure only 1 active AtcImport
                AtcImport.objects.exclude(pk=self.pk).update(active=False)
            super().save(*args, **kwargs)

    def __str__(self):
        return self.timestamp.strftime('%d-%m-%Y')


class FdaImport(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    drug_aliases_inserted = models.IntegerField(default=0)


class WhoAtc(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=7, db_index=True)
    atc_import = models.ForeignKey(on_delete=models.CASCADE, related_name="%(class)ss")
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
    pass


class TherapeuticMainGroup(WhoAtc):
    parent = models.ForeignKey(AnatomicalMainGroup, on_delete=models.CASCADE)


class TherapeuticPharmacologicalSubgroup(WhoAtc):
    parent = models.ForeignKey(TherapeuticMainGroup, on_delete=models.CASCADE)


class ChemicalTherapeuticPharmacologicalSubgroup(WhoAtc):
    parent = models.ForeignKey(TherapeuticPharmacologicalSubgroup, on_delete=models.CASCADE)


class ChemicalSubstance(WhoAtc):
    parent = models.ForeignKey(ChemicalTherapeuticPharmacologicalSubgroup, on_delete=models.CASCADE)

    @classmethod
    def create_drug_batches(cls, batch_size=50):
        queryset = cls.objects.all()
        total = queryset.count()

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            yield queryset[start:end]