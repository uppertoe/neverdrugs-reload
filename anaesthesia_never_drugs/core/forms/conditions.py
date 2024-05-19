from django import forms
from datetime import datetime

from ..models.conditions import OrphaEntry


class OrphaEntryForm(forms.ModelForm):
    
    class Meta:
        model = OrphaEntry
        fields = ['name', 'orpha_code', 'date_updated', 'status', 'description']
        input_formats = {
            'date_updated': ['%Y-%m-%d %H:%M:%S'],
        }

        # Specify the OrphaInstance in the kwargs

    def __init__(self, *args, **kwargs):
        self.orpha_import_instance = kwargs.pop('orpha_import_instance', None)
        super().__init__(*args, **kwargs)

    def clean_date_updated(self):
        # Convert the date_updated to a DateTime object
        date_string = self.cleaned_data.get('date_updated')
        print(date_string)
        if isinstance(date_string, str):
            try:
                date_format = '%Y-%m-%d %H:%M:%S'
                return datetime.strptime(date_string, date_format)
            except ValueError:
                raise forms.ValidationError("Incorrect date format, should be YYYY-MM-DD HH:MM:SS")
        return date_string
    
    def clean_description(self):
        # Replace 'None available' with an empty string
        description_string = self.cleaned_data.get('description')
        return '' if description_string == 'None available' else description_string

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Attach the Orpha Import to the instance
        instance.orpha_import = self.orpha_import_instance

        if commit:
            instance.save()
        return instance