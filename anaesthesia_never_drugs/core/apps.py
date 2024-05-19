from django.apps import AppConfig


class CoreAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "anaesthesia_never_drugs.core"
    label = "core"

    def ready(self):
        from . import signals