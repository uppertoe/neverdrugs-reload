from django.db import models

from . import classifications

#Drugs

class Drug(models.Model):
    name = models.CharField(max_length=255)
    atc_category = models.ManyToManyField(classifications.ChemicalSubstance, through='DrugCategory')
    searchable = models.BooleanField(default=True)

    def get_category_parents(self):
        chemical_substances = self.atc_category.all()
        parent = classifications.ChemicalTherapeuticPharmacologicalSubgroup 
        
        parents = parent.objects.filter(chemicalsubstance__in=chemical_substances).distinct()

        return parents

    def get_related_drugs(self):
        # Find drugs related to the same categories as this drug, excluding the current drug
        parents = self.get_category_parents()
        children = classifications.ChemicalSubstance.objects.filter(parent__in=parents)

        related_drugs = Drug.objects.exclude(pk=self.pk).filter(atc_category__in=children)

        return related_drugs
    
    def get_categories(self):
        content = []
        for category in self.atc_category.all():
            content.append(str(category.parent))
        return ', '.join(content)
    
    def get_search_index_data(self):

        return {'name': self.name,
                'content': self.get_categories(),
                'searchable': self.searchable}

    def __str__(self):
        return self.name


class DrugCategory(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='drug_categories')
    # Ensure ChemicalSubstances pointing to a drug are not deleted
    category = models.ForeignKey(classifications.ChemicalSubstance, on_delete=models.PROTECT, related_name='drug_categories')

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