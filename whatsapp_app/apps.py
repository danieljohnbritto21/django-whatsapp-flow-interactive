from django.apps import AppConfig


class WhatsappAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_app'
    verbose_name = 'Thaagam Foundation WhatsApp Donation System'

    def ready(self):
        from . import scheduler
        scheduler.start()