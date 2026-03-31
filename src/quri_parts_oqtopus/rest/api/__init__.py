# flake8: noqa

if __import__("typing").TYPE_CHECKING:
    # import apis into api package
    from quri_parts_oqtopus.rest.api.announcements_api import AnnouncementsApi
    from quri_parts_oqtopus.rest.api.settings_api import SettingsApi
    from quri_parts_oqtopus.rest.api.users_api import UsersApi
    from quri_parts_oqtopus.rest.api.api_token_api import ApiTokenApi
    from quri_parts_oqtopus.rest.api.device_api import DeviceApi
    from quri_parts_oqtopus.rest.api.job_api import JobApi
    
else:
    from lazy_imports import LazyModule, as_package, load

    load(
        LazyModule(
            *as_package(__file__),
            """# import apis into api package
from quri_parts_oqtopus.rest.api.announcements_api import AnnouncementsApi
from quri_parts_oqtopus.rest.api.settings_api import SettingsApi
from quri_parts_oqtopus.rest.api.users_api import UsersApi
from quri_parts_oqtopus.rest.api.api_token_api import ApiTokenApi
from quri_parts_oqtopus.rest.api.device_api import DeviceApi
from quri_parts_oqtopus.rest.api.job_api import JobApi

""",
            name=__name__,
            doc=__doc__,
        )
    )
