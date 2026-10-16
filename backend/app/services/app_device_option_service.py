from app.schemas.app_device import DeviceOptionsQuery
from app.services.resource_option_service import ResourceOptionService


class AppDeviceOptionService:
    """Physical pool devices can be reused without changing their project binding."""

    def __init__(self, repository):
        self.options = ResourceOptionService("app_devices", repository)

    def list_options(self, query: DeviceOptionsQuery):
        return self.options.list_options(None if query.scope == "pool" else query.project_id)
