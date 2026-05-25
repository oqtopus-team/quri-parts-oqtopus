from quri_parts_oqtopus.backend.base import OqtopusBackendBase
from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.models.devices.device import OqtopusDevice


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

    def get_devices(self) -> list[OqtopusDevice]:
        """Get all devices registered in Oqtopus Cloud.

        Returns:
            list[OqtopusDevice]: A list of OqtopusDevice objects.

        """
        raw_devices = self._client.list_devices()
        return [OqtopusDevice(dev, self._client) for dev in raw_devices]

    def get_device(self, device_id: str) -> OqtopusDevice:
        """Get a device by its ID.

        Args:
            device_id (str): The ID of the device.

        Returns:
            OqtopusDevice: An OqtopusDevice object.

        """
        raw_dev = self._client.get_device(device_id)
        return OqtopusDevice(raw_dev, self._client)
