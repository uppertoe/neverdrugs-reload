from django.apps import AppConfig


class CoreAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "anaesthesia_never_drugs.core"
    label = "core"

    def ready(self):
        from . import signals
        from .tasks import cache_common_queries
        
        # Trigger caching of common queries at startup
        cache_common_queries.delay()