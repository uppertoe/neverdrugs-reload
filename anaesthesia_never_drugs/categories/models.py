from django.db import models


# Implementation of the Anatomical Therapeutic Chemical (ATC) Classification System

class WhoAtc(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=7, db_index=True)

    @staticmethod
    def get_model_by_level(level):
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


# Drugs

class Drug(models.Model):
    name = models.CharField(max_length=255)
    atc_category = models.ManyToManyField(ChemicalSubstance, through='DrugCategory')

    def get_related_drugs(self):
        # Find drugs related to the same categories as this drug, excluding the current drug
        related_drugs = Drug.objects.filter(
            atc_category__in=self.atc_category.all()
        ).distinct().exclude(id=self.id)

        return related_drugs

    def __str__(self):
        return self.name


class DrugCategory(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    category = models.ForeignKey(ChemicalSubstance, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.category}: {self.drug}'


class Source(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=255)

    def __str__(self):
        return self.name


class DrugAlias(models.Model):
    name = models.CharField(max_length=255)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.name} ({self.drug})'