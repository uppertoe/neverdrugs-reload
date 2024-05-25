from django.contrib import admin

from .models.classifications import AtcImport, AnatomicalMainGroup, TherapeuticMainGroup, TherapeuticPharmacologicalSubgroup, ChemicalTherapeuticPharmacologicalSubgroup, ChemicalSubstance
from .models.search import SearchIndex, SearchQueryLog
from .models.drugs import Drug, DrugCategory, Source, DrugAlias
from .models.conditions import OrphaImport, Condition, ConditionSynonym, ConditionOrphaCategory, OrphaCategory, OrphaEntry

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

class DrugAdminInline(admin.TabularInline):
    model = DrugCategory
    extra = 1

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'searchable')
    inlines = (DrugAdminInline,)

@admin.register(DrugCategory)
class DrugCategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    pass

@admin.register(DrugAlias)
class DrugAliasAdmin(admin.ModelAdmin):
    pass

@admin.register(OrphaImport)
class OrphaImportAdmin(admin.ModelAdmin):
    pass

@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    pass

@admin.register(OrphaEntry)
class OrphaEntryAdmin(admin.ModelAdmin):
    pass

@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ('query', 'count')