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

        if not celery_broker_url or celery_broker_url == "/":
            logger.info("CELERY_BROKER_URL is not set. Skipping Redis initialization.")
        else:
            try:
                from .tasks import cache_common_queries
                cache_common_queries.delay()
                logger.info("Triggered cache_common_queries successfully.")
            except Exception as e:
                logger.error(f"Failed to trigger cache_common_queries: {e}")