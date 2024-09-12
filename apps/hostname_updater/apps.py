from django.apps import AppConfig


class HostnameUpdaterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hostname_updater'
    def ready(self):
        import apps.hostname_updater.templatetags.form_tags
