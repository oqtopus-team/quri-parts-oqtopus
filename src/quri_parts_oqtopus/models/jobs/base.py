import json
import time
from abc import abstractmethod
from datetime import datetime
from typing import Any, cast

from oqtopus_client import OqtopusClient
from oqtopus_client.services.job_results import (
    OqtopusJobResult,
)
from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.models.base import OqtopusModelBase
from quri_parts_oqtopus.models.jobs.results.estimation import OqtopusEstimationResult
from quri_parts_oqtopus.models.jobs.results.sampling import OqtopusSamplingResult
from quri_parts_oqtopus.models.utils import DateTimeEncoder

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


def _str_value(value: object) -> str:
    raw_value = value.value if hasattr(value, "value") else value
    return str(raw_value)


def _to_dict(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return cast("dict[str, Any]", value.to_dict())
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return cast("dict[str, Any]", value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, dict):
        return value
    return {}


class OqtopusJobBase(OqtopusModelBase):  # noqa: PLR0904
    """A base class for OQTOPUS jobs.

    This class provides common functions for OQTOPUS jobs.
    """

    def __init__(self, job: OqtopusJobResult, client: OqtopusClient) -> None:
        super().__init__()

        if job is None:
            msg = "'job' should not be None"
            raise ValueError(msg)
        self._job = job

        if client is None:
            msg = "'client' should not be None"
            raise ValueError(msg)
        self._client = client

    @property
    def job_id(self) -> str:
        """The id of the job.

        Returns:
            str: The id of the job.

        """
        return str(self._job.job_id)

    @property
    def name(self) -> str:
        """The name of the job.

        Returns:
            str: The name of the job.

        """
        return self._job.name or ""

    @property
    def description(self) -> str:
        """The description of the job.

        Returns:
            str: The description of the job.

        """
        return self._job.description or ""

    @property
    def job_type(self) -> str:
        """The job type of the job.

        Returns:
            str: The job type of the job.

        """
        return _str_value(self._job.job_type)

    @property
    def status(self) -> str:
        """The status of the job.

        Returns:
            str: The status of the job.

        """
        return _str_value(self._job.status)

    @property
    def device_id(self) -> str:
        """The device id of the job.

        Returns:
            str: The device id of the job.

        """
        return self._job.device_id or ""

    @property
    def shots(self) -> int:
        """The shots of the job.

        Returns:
            int: The shots of the job.

        """
        return self._job.shots or 0

    @property
    def job_info(self) -> dict:
        """The detail information of the job.

        Returns:
            dict: The detail information of the job.

        """
        return _to_dict(self._job.job_info)

    @property
    def transpiler_info(self) -> dict:
        """The transpiler info of the job.

        Returns:
            dict: The transpiler info of the job.

        """
        return dict(self._job.transpiler_info or {})

    @property
    def simulator_info(self) -> dict:
        """The simulator info of the job.

        Returns:
            dict: The simulator info of the job.

        """
        return dict(self._job.simulator_info or {})

    @property
    def mitigation_info(self) -> dict:
        """The mitigation info of the job.

        Returns:
            dict: The mitigation info of the job.

        """
        return dict(self._job.mitigation_info or {})

    @property
    def execution_time(self) -> float:
        """The execution time of the job.

        Returns:
            float: The execution time of the job.

        """
        return float(self._job.execution_time or 0.0)

    @property
    def submitted_at(self) -> datetime:
        """The `submitted_at` of the job.

        Returns:
            datetime: The `submitted_at` of the job.

        """
        return cast("datetime", self._job.submitted_at)

    @property
    def ready_at(self) -> datetime:
        """The `ready_at` of the job.

        Returns:
            datetime: The `ready_at` of the job.

        """
        return cast("datetime", self._job.ready_at)

    @property
    def running_at(self) -> datetime:
        """The `running_at` of the job.

        Returns:
            datetime: The `running_at` of the job.

        """
        return cast("datetime", self._job.running_at)

    @property
    def ended_at(self) -> datetime:
        """The `ended_at` of the job.

        Returns:
            datetime: The `ended_at` of the job.

        """
        return cast("datetime", self._job.ended_at)

    @abstractmethod
    def result(
        self, timeout: float | None = None, wait: float = 10.0
    ) -> OqtopusSamplingResult | OqtopusEstimationResult:
        """Wait until the job progress to the end and returns the result of the job.

        If the status of job is not ``succeeded`` or ``failed``, or ``cancelled``,
        the job is retrieved from OQTOPUS Cloud at intervals of ``wait`` seconds.
        If the job does not progress to the end after ``timeout`` seconds,
        raise :class:`BackendError`.

        Args:
            timeout: The number of seconds to wait for job.
            wait: Time in seconds between queries.

        Returns:
            OqtopusSamplingResult | OqtopusEstimationResult: The result of the job.
                Returns OqtopusSamplingResult for sampling jobs or
                OqtopusEstimationResult for estimation jobs.

        Raises:
            BackendError: If job cannot be found or if an authentication error occurred
                or timeout occurs, etc.

        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)

    def refresh(self) -> None:
        """Retrieve the latest job information from OQTOPUS Cloud.

        Raises:
            BackendError: If job cannot be found or if an authentication error occurred
                or timeout occurs, etc.

        """
        try:
            self._job = self._client.get_job(self.job_id)
        except Exception as e:
            msg = "To refresh job is failed."
            raise BackendError(msg) from e

    def wait_for_completion(
        self, timeout: float | None = None, wait: float = 10.0
    ) -> OqtopusJobResult | None:
        """Wait until the job progress to the end.

        Calling this function waits until the job progress to the end such as
        ``succeeded`` or ``failed``, ``cancelled``.

        Args:
            timeout: The number of seconds to wait for job.
            wait: Time in seconds between queries.

        Returns:
            OqtopusJobResult | None: If a timeout occurs, it returns None. Otherwise, it
                returns the Job.

        """
        start_time = time.time()
        self.refresh()
        while self.status not in JOB_FINAL_STATUS:
            # check timeout
            elapsed_time = time.time() - start_time
            if timeout is not None and elapsed_time >= timeout:
                return None

            # sleep and get job
            time.sleep(wait)
            self.refresh()

        return self._job

    def cancel(self) -> None:
        """Cancel the job.

        If the job statuses are success, failure, or cancelled,
        then cannot be cancelled and an error occurs.

        Raises:
            BackendError: If job cannot be found or if an authentication error occurred
                or if job cannot be cancelled, etc.

        """
        try:
            self._client.cancel_job(self.job_id)
            self.refresh()
        except Exception as e:
            msg = "To cancel job is failed."
            raise BackendError(msg) from e

    def to_json(self) -> str:
        """Return a json string representation of the OqtopusJobBase.

        Returns:
            str: A json string representation of the OqtopusJobBase.

        """
        payload = {
            "job_id": self.job_id,
            "name": self.name,
            "description": self.description,
            "job_type": self.job_type,
            "status": self.status,
            "device_id": self.device_id,
            "shots": self.shots,
            "job_info": self.job_info,
            "transpiler_info": self.transpiler_info,
            "simulator_info": self.simulator_info,
            "mitigation_info": self.mitigation_info,
            "execution_time": self.execution_time,
            "submitted_at": self.submitted_at,
            "ready_at": self.ready_at,
            "running_at": self.running_at,
            "ended_at": self.ended_at,
        }
        return json.dumps(payload, cls=DateTimeEncoder)
