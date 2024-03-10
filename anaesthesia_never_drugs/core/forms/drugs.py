from django import forms

from ..exceptions import UnsupportedAtcLevelException
from ..models.classifications import WhoAtc, AnatomicalMainGroup, TherapeuticMainGroup, TherapeuticPharmacologicalSubgroup, ChemicalTherapeuticPharmacologicalSubgroup, ChemicalSubstance


class WhoAtcForm(forms.ModelForm):  # Abstract base class
    level = forms.IntegerField(min_value=1, max_value=5)

    class Meta:
        fields = ['name', 'code']  # Implemented in all subclass models

    def __init__(self, *args, **kwargs):
        self.atc_import_instance = kwargs.pop('atc_import_instance', None)
        self.root_name = kwargs.pop('root_name', None)
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Attach the parent model to the instance
        level = self.cleaned_data.get('level')
        parent_code = self.cleaned_data.get('parent')

        if level and parent_code:
            ParentModel = WhoAtc.get_model_by_level(level - 1) if level > 1 else None
            if ParentModel:
                root_name = self.root_name if level == 2 else None  # Ensure level 1 is named by its child
                parent_instance, _ = ParentModel.objects.get_or_create(
                    code=parent_code,
                    atc_import=self.atc_import_instance,
                    name=root_name,
                    )
                instance.parent = parent_instance
            else:
                # Note no parent for level 1
                raise UnsupportedAtcLevelException(f"Invalid ATC level supplied by web scraper: level {level}")
        if commit:
            instance.save()
        return instance


class AnatomicalMainGroupForm(WhoAtcForm):
    class Meta:
        model = AnatomicalMainGroup

class TherapeuticMainGroupForm(WhoAtcForm):
    class Meta:
        model = TherapeuticMainGroup


class TherapeuticPharmacologicalSubgroupForm(WhoAtcForm):
    class Meta:
        model = TherapeuticPharmacologicalSubgroup

class ChemicalTherapeuticPharmacologicalSubgroupForm(WhoAtcForm):
    class Meta:
        model = ChemicalTherapeuticPharmacologicalSubgroup


class ChemicalSubstanceForm(forms.ModelForm):
    class Meta:
        model = ChemicalSubstance

FORMS_BY_LEVEL = {1: AnatomicalMainGroupForm,
            2: TherapeuticMainGroupForm,
            3: TherapeuticPharmacologicalSubgroupForm,
            4: ChemicalTherapeuticPharmacologicalSubgroupForm,
            5: ChemicalSubstanceForm,
            }