from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class CoreAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "anaesthesia_never_drugs.core"
    label = "core"

    def ready(self):
        from . import signals

        # Check if CELERY_BROKER_URL is available before triggering caching
        celery_broker_url = os.getenv('CELERY_BROKER_URL')
        
        if celery_broker_url:
            from .tasks import cache_common_queries
            cache_common_queries.delay()
        else:
            logger.info("CELERY_BROKER_URL is not set. Skipping Redis initialization.")