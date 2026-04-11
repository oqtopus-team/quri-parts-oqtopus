from quri_parts_oqtopus.backend.base import OqtopusBackendBase
from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.models.devices.device import OqtopusDevice
from quri_parts_oqtopus.rest import (
    DeviceApi,
)


class OqtopusDeviceBackend(OqtopusBackendBase):
    """A class representing a device backend for Oqtopus.

    This class is a placeholder and does not implement any functionality.
    It serves as a base for creating specific device backends in the future.
    """

    def __init__(
        self,
        config: OqtopusConfig | None = None,
    ) -> None:
        super().__init__(config=config)

        self._device_api: DeviceApi = DeviceApi(api_client=self._api_client)

    def get_devices(self) -> list[OqtopusDevice]:
        """Get all devices registered in Oqtopus Cloud.

        Returns:
            list[OqtopusDevice]: A list of OqtopusDevice objects.

        """
        raw_devices = self._device_api.list_devices()
        return [OqtopusDevice(dev, self._device_api) for dev in raw_devices]

    def get_device(self, device_id: str) -> OqtopusDevice:
        """Get a device by its ID.

        Args:
            device_id (str): The ID of the device.

        Returns:
            OqtopusDevice: An OqtopusDevice object.

        """
        raw_dev = self._device_api.get_device(device_id)
        return OqtopusDevice(raw_dev, self._device_api)
