from django.apps import AppConfig

class PluginApp(AppConfig):
    name = 'pretix_nexum_summary'
    verbose_name = 'NEXUM spoločný prehľad'

    class PretixPluginMeta:
        name = 'NEXUM spoločný prehľad'
        author = 'Marketeam'
        version = '0.1.0'
        category = 'FEATURE'
        description = 'Read-only súčet pôvodného a nového novoročného predaja.'
        compatibility = 'pretix>=2025.11.0.dev0,<2026'

    def ready(self):
        from . import signals  # noqa: F401
