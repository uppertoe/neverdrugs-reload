from django.apps import AppConfig
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CoreAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "anaesthesia_never_drugs.core"
    label = "core"

    def ready(self):
        from . import signals

        # Ensure ENVs are available
        if settings.CELERY_BROKER_URL:
            # Trigger caching of common queries at startup
            from .tasks import cache_common_queries
            cache_common_queries.delay()
        else:
            logger.info("CELERY_BROKER_URL is not set. Skipping Redis initialization.")