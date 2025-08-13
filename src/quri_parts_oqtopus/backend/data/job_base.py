import json
import time
from abc import abstractmethod
from datetime import datetime

from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.backend.model_base import OqtopusModelBase
from quri_parts_oqtopus.backend.utils import DateTimeEncoder
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusJobBase(OqtopusModelBase):  # noqa: PLR0904
    """A base class for OQTOPUS jobs.

    This class provides common functionality for all job types in the OQTOPUS framework.
    """

    def __init__(self, job: JobsJobDef, job_api: JobApi) -> None:
        super().__init__()

        if job is None:
            msg = "'job' should not be None"
            raise ValueError(msg)
        self._job: JobsJobDef = job

        if job_api is None:
            msg = "'job_api' should not be None"
            raise ValueError(msg)
        self._job_api: JobApi = job_api

    @property
    def job_id(self) -> str:
        """The id of the job.

        Returns:
            str: The id of the job.

        """
        return self._job.job_id

    @property
    def name(self) -> str:
        """The name of the job.

        Returns:
            str: The name of the job.

        """
        return self._job.name

    @property
    def description(self) -> str:
        """The description of the job.

        Returns:
            str: The description of the job.

        """
        return self._job.description

    @property
    def job_type(self) -> str:
        """The job type of the job.

        Returns:
            str: The job type of the job.

        """
        return self._job.job_type

    @property
    def status(self) -> str:
        """The status of the job.

        Returns:
            str: The status of the job.

        """
        return self._job.status

    @property
    def device_id(self) -> str:
        """The device id of the job.

        Returns:
            str: The device id of the job.

        """
        return self._job.device_id

    @property
    def shots(self) -> int:
        """The shots of the job.

        Returns:
            int: The shots of the job.

        """
        return self._job.shots

    @property
    def job_info(self) -> dict:
        """The detail information of the job.

        Returns:
            dict: The detail information of the job.

        """
        return self._job.job_info.to_dict()

    @property
    def transpiler_info(self) -> dict:
        """The transpiler info of the job.

        Returns:
            dict: The transpiler info of the job.

        """
        return self._job.transpiler_info

    @property
    def simulator_info(self) -> dict:
        """The simulator info of the job.

        Returns:
            dict: The simulator info of the job.

        """
        return self._job.simulator_info

    @property
    def mitigation_info(self) -> dict:
        """The mitigation info of the job.

        Returns:
            dict: The mitigation info of the job.

        """
        if self._job.mitigation_info:
            return json.loads(self._job.mitigation_info)
        return {}

    @property
    def execution_time(self) -> float:
        """The execution time of the job.

        Returns:
            float: The execution time of the job.

        """
        return self._job.execution_time

    @property
    def submitted_at(self) -> datetime:
        """The `submitted_at` of the job.

        Returns:
            datetime: The `submitted_at` of the job.

        """
        return self._job.submitted_at

    @property
    def ready_at(self) -> datetime:
        """The `ready_at` of the job.

        Returns:
            datetime: The `ready_at` of the job.

        """
        return self._job.ready_at

    @property
    def running_at(self) -> datetime:
        """The `running_at` of the job.

        Returns:
            datetime: The `running_at` of the job.

        """
        return self._job.running_at

    @property
    def ended_at(self) -> datetime:
        """The `ended_at` of the job.

        Returns:
            datetime: The `ended_at` of the job.

        """
        return self._job.ended_at

    @abstractmethod
    def result(self, timeout: float | None = None, wait: float = 10.0) -> object:
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
            self._job = self._job_api.get_job(self._job.job_id)
        except Exception as e:
            msg = "To refresh job is failed."
            raise BackendError(msg) from e

    def wait_for_completion(
        self, timeout: float | None = None, wait: float = 10.0
    ) -> JobsJobDef | None:
        """Wait until the job progress to the end.

        Calling this function waits until the job progress to the end such as
        ``succeeded`` or ``failed``, ``cancelled``.

        Args:
            timeout: The number of seconds to wait for job.
            wait: Time in seconds between queries.

        Returns:
            JobsJobDef | None: If a timeout occurs, it returns None. Otherwise, it
                returns the Job.

        """
        start_time = time.time()
        self.refresh()
        while self._job.status not in JOB_FINAL_STATUS:
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
            self._job_api.cancel_job(self._job.job_id)
            self.refresh()
        except Exception as e:
            msg = "To cancel job is failed."
            raise BackendError(msg) from e

    def to_json(self) -> str:
        """Return a json string representation of the OqtopusJobBase.

        Returns:
            str: A json string representation of the OqtopusJobBase.

        """
        return json.dumps(self._job.to_dict(), cls=DateTimeEncoder)
