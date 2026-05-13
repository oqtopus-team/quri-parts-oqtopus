import json
from datetime import datetime
from typing import cast

from oqtopus_client import OqtopusClient
from oqtopus_client.services.device import OqtopusDevice as ClientDevice
from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.models.base import OqtopusModelBase
from quri_parts_oqtopus.models.utils import DateTimeEncoder


class OqtopusDevice(OqtopusModelBase):
    """A device embedded in the oqtopus framework.

    Args:
        device: The device information.
        client: The client for communication with the backend.

    Raises:
        ValueError: If the device or client is None.

    """

    def __init__(self, device: ClientDevice, client: OqtopusClient) -> None:
        super().__init__()

        if device is None:
            msg = "'device' should not be None"
            raise ValueError(msg)
        if client is None:
            msg = "'client' should not be None"
            raise ValueError(msg)

        self._device = device
        self._client = client

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
        return cast("datetime", self._device.available_at)

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
        return self._device.n_qubits or 0

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
        try:
            return self._device.device_info or {}
        except json.JSONDecodeError:
            return {}

    @property
    def calibrated_at(self) -> datetime:
        """The `calibrated_at` of this DevicesDeviceInfo.

        Returns:
            datetime: The `calibrated_at` of this DevicesDeviceInfo.

        """
        return cast("datetime", self._device.calibrated_at)

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
            self._device = self._client.get_device(self.device_id)
        except Exception as e:
            msg = "failed to refresh device info"
            raise BackendError(msg) from e

    def to_json(self) -> str:
        """Return a json string representation of the OqtopusDevice.

        Returns:
            str: A json string representation of the OqtopusDevice.

        """
        return json.dumps(self._device.raw.to_dict(), cls=DateTimeEncoder)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusDevice.

        Returns:
            str: A string representation of the OqtopusDevice.

        """
        return self._device.raw.to_str()
