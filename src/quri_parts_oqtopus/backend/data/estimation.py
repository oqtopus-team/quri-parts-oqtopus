from typing import Any

from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend.data.job_base import OqtopusJobBase
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusEstimationResult:
    """A result of a estimation job.

    Args:
        result: A result of dict type.

    Raises:
        ValueError: If ``estimation`` does not exist in result.

    Examples:
        An example of a dict of result is as below:

        .. code-block::

            {
                "estimation": {
                    "exp_value": 2.0,
                    "stds": 1.1
                }
            }

        ``exp_value`` represents the expectation value.
        In the above case, ``exp_value`` is defined as a real number ``2.0``.
        ``stds`` represents the standard deviation value.

    """

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__()

        self._result = result

    @property
    def exp_value(self) -> float | None:
        """Returns the expectation value."""
        return self._result.get("exp_value")

    @property
    def stds(self) -> float | None:
        """Returns the  standard deviation."""
        return self._result.get("stds")

    def __repr__(self) -> str:
        """Return a string representation.

        Returns:
            str: A string representation.

        """
        return str(self._result)


class OqtopusEstimationJob(OqtopusJobBase):
    """A job for a estimation.

    Args:
        job: A result of dict type.
        job_api: A result of dict type.

    Raises:
        ValueError: If ``job`` or ``job_api`` is None.

    """

    def __init__(self, job: JobsJobDef, job_api: JobApi) -> None:
        super().__init__(job=job, job_api=job_api)

    def result(
        self, timeout: float | None = None, wait: float = 10.0
    ) -> OqtopusEstimationResult:
        """Wait until the job progress to the end and returns the result of the job.

        If the status of job is not ``succeeded`` or ``failed``, or ``cancelled``,
        the job is retrieved from OQTOPUS Cloud at intervals of ``wait`` seconds.
        If the job does not progress to the end after ``timeout`` seconds,
        raise :class:`BackendError`.

        Args:
            timeout: The number of seconds to wait for job.
            wait: Time in seconds between queries.

        Returns:
            OqtopusEstimationResult: the result of the estimation job.

        Raises:
            BackendError: If job cannot be found or if an authentication error occurred
                or timeout occurs, etc.

        """
        if self._job.status not in JOB_FINAL_STATUS:
            job = self.wait_for_completion(timeout, wait)
            if job is None:
                msg = f"Timeout occurred after {timeout} seconds."
                raise BackendError(msg)
            self._job = job
        if self._job.status in {"failed", "cancelled"}:
            msg = f"Job ended with status {self._job.status}."
            raise BackendError(msg)

        # edit json for OqtopusEstimationResult
        result = self.job_info["result"]["estimation"]

        return OqtopusEstimationResult(result)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusEstimationJob.

        Returns:
            str: A string representation of the OqtopusEstimationJob.

        """
        return self._job.to_str()
