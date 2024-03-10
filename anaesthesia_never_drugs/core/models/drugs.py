from django.db import models

from . import classifications

#Drugs

class Drug(models.Model):
    name = models.CharField(max_length=255)
    atc_category = models.ManyToManyField(classifications.ChemicalSubstance, through='DrugCategory')
    searchable = models.BooleanField(default=True)

    def get_related_drugs(self):
        # Find drugs related to the same categories as this drug, excluding the current drug
        related_drugs = Drug.objects.filter(
            atc_category__in=self.atc_category.filter(atc_import__active=True)
        ).distinct().exclude(id=self.id)

        return related_drugs
    
    def get_search_index_data(self):
        return {'name': self.name,
                'content': '',
                'searchable': self.searchable}

    def __str__(self):
        return self.name


class DrugCategory(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='drug_categories')
    category = models.ForeignKey(classifications.ChemicalSubstance, on_delete=models.CASCADE, related_name='drug_categories')

    def __str__(self):
        return f'{self.category}: {self.drug}'
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['drug', 'category'], name='unique_drug_category')
        ]


class Source(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=510, blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    citation = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class DrugAlias(models.Model):
    name = models.CharField(max_length=255)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='drug_aliases')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='drug_aliases')
    searchable = models.BooleanField(default=True)

    def get_search_index_data(self):
        return {'name': self.name,
                'content': '',
                'searchable': self.searchable}
    
    def __str__(self):
        return f'{self.name} ({self.drug})'