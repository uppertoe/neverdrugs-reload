from django.contrib import admin

from .models.classifications import AtcImport, AnatomicalMainGroup, TherapeuticMainGroup, TherapeuticPharmacologicalSubgroup, ChemicalTherapeuticPharmacologicalSubgroup, ChemicalSubstance
from .models.search import SearchIndex

@admin.register(AtcImport)
class AtcImportAdmin(admin.ModelAdmin):
    pass

@admin.register(AnatomicalMainGroup)
class AnatomicalMainGroupAdmin(admin.ModelAdmin):
    pass

@admin.register(TherapeuticMainGroup)
class TherapeuticMainGroup(admin.ModelAdmin):
    pass

@admin.register(TherapeuticPharmacologicalSubgroup)
class TherapeuthicPharmacologicalSubgroupAdmin(admin.ModelAdmin):
    pass

@admin.register(ChemicalTherapeuticPharmacologicalSubgroup)
class ChemicalTherapeuticPharmacologicalSubgroupAdmin(admin.ModelAdmin):
    pass

@admin.register(ChemicalSubstance)
class ChemicalSubstanceAdmin(admin.ModelAdmin):
    pass

@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    pass