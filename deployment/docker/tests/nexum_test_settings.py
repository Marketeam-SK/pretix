from tests.settings import *  # noqa: F403

# Pretix's regular test settings remove installed external plugins.
INSTALLED_APPS = [*INSTALLED_APPS, 'pretix_nexum_summary']  # noqa: F405
