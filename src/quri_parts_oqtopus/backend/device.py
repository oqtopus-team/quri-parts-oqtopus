import json
import os
from datetime import datetime

from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.backend.utils import DateTimeEncoder
from quri_parts_oqtopus.rest import (
    ApiClient,
    Configuration,
    DeviceApi,
    DevicesDeviceInfo,
)


class OqtopusDevice:
    """A device embedded in the oqtopus framework.

    Args:
        device: The device information.
        device_api: The device API for communication with the backend.

    Raises:
        ValueError: If the device or device_api is None.

    """

    def __init__(self, device: DevicesDeviceInfo, device_api: DeviceApi) -> None:
        if device is None:
            msg = "'device' should not be None"
            raise ValueError(msg)
        if device_api is None:
            msg = "'device_api' should not be None"
            raise ValueError(msg)

        self._device: DevicesDeviceInfo = device
        self._device_api: DeviceApi = device_api

    @property
    def device_id(self) -> str:
        """The device id of the device.

        Returns:
            str: The device id of the device.

        """
        return self._device.device_id

    @property
    def device_type(self) -> str:
        """The device type of the device.

        Returns:
            str: The device type of the device.

        """
        return self._device.device_type

    @property
    def status(self) -> str:
        """The status of the device.

        Returns:
            str: The status of the device.

        """
        return self._device.status

    @property
    def available_at(self) -> datetime:
        """The `available_at` of this DevicesDeviceInfo.

        Returns:
            datetime: The `available_at` of this DevicesDeviceInfo.

        """
        return self._device.available_at

    @property
    def n_pending_jobs(self) -> int:
        """The number of pending jobs in the device.

        Returns:
            int: The number of pending jobs in the device.

        """
        return self._device.n_pending_jobs

    @property
    def n_qubits(self) -> int:
        """The number of qubits in the device.

        Returns:
            int: The number of qubits in the device.

        """
        return self._device.n_qubits

    @property
    def basis_gates(self) -> list[str]:
        """The basis gates of the device.

        Returns:
            list[str]: The basis gates of the device.

        """
        return self._device.basis_gates

    @property
    def supported_instructions(self) -> list[str]:
        """The supported instructions of the device.

        Returns:
            list[str]: The supported instructions of the device.

        """
        return self._device.supported_instructions

    @property
    def device_info(self) -> dict:
        """The device information of the device.

        Returns:
            dict: The device information of the device.

        """
        return self._device.device_info

    @property
    def calibrated_at(self) -> datetime:
        """The `calibrated_at` of this DevicesDeviceInfo.

        Returns:
            datetime: The `calibrated_at` of this DevicesDeviceInfo.

        """
        return self._device.calibrated_at

    @property
    def description(self) -> str:
        """The description of the device.

        Returns:
            str: The description of the device.

        """
        return self._device.description

    def refresh(self) -> None:
        """Retrieve the device information from OQTOPUS Cloud.

        Raises:
            BackendError: If device cannot be found
                or if an authentication error occurred
                    or timeout occurs, etc.

        """
        try:
            self._device = self._device_api.get_device(self.device_id)
        except Exception as e:
            msg = "failed to refresh device info"
            raise BackendError(msg) from e

    def to_json(self) -> str:
        """Return a json string representation of the OqtopusDevice.

        Returns:
            str: A json string representation of the OqtopusDevice.

        """
        return json.dumps(self._device.to_dict(), cls=DateTimeEncoder)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusDevice.

        Returns:
            str: A string representation of the OqtopusDevice.

        """
        return self._device.to_str()


class OqtopusDeviceBackend:
    """A class representing a device backend for Oqtopus.

    This class is a placeholder and does not implement any functionality.
    It serves as a base for creating specific device backends in the future.
    """

    def __init__(
        self,
        config: OqtopusConfig | None = None,
    ) -> None:
        super().__init__()

        # set config
        if config is None:
            # if environment variables are set, use their values
            url = os.getenv("OQTOPUS_URL")
            api_token = os.getenv("OQTOPUS_API_TOKEN")
            proxy = os.getenv("OQTOPUS_PROXY")
            if url is not None and api_token is not None:
                config = OqtopusConfig(
                    url=url,
                    api_token=api_token,
                    proxy=proxy,
                )
            # load config from file
            else:
                config = OqtopusConfig.from_file()

        # construct DeviceApi
        rest_config = Configuration()
        rest_config.host = config.url
        if config.proxy:
            rest_config.proxy = config.proxy
        api_client = ApiClient(
            configuration=rest_config,
            header_name="q-api-token",
            header_value=config.api_token,
        )
        self._device_api: DeviceApi = DeviceApi(api_client=api_client)

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
