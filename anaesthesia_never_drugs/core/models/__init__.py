# Import submodels to ensure discoverability by django
from .classifications import AtcImport, FdaImport, WhoAtc, AnatomicalMainGroup, TherapeuticMainGroup, TherapeuticPharmacologicalSubgroup, ChemicalTherapeuticPharmacologicalSubgroup, ChemicalSubstance
from .drugs import Drug, DrugCategory, Source, DrugAlias
from .search import SearchIndex