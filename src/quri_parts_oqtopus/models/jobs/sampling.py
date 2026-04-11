import json
from collections import Counter

from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.models.jobs.base import OqtopusJobBase
from quri_parts_oqtopus.models.jobs.results.sampling import (
    OqtopusSamplingResult,
)
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusSamplingJob(OqtopusJobBase):
    """A job for a sampling measurement.

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
    ) -> OqtopusSamplingResult:
        """Wait until the job progress to the end and returns the result of the job.

        If the status of job is not ``succeeded`` or ``failed``, or ``cancelled``,
        the job is retrieved from OQTOPUS Cloud at intervals of ``wait`` seconds.
        If the job does not progress to the end after ``timeout`` seconds,
        raise :class:`BackendError`.

        Args:
            timeout: The number of seconds to wait for job.
            wait: Time in seconds between queries.

        Returns:
            OqtopusSamplingResult: the result of the sampling job.

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

        # edit json for OqtopusSamplingResult
        result = self.job_info["result"]["sampling"]
        if isinstance(result["counts"], str):
            result["counts"] = json.loads(result["counts"])
        result["counts"] = Counter({
            int(bits, 2) if isinstance(bits, str) else bits: count
            for bits, count in result["counts"].items()
        })

        if result.get("divided_counts"):
            if isinstance(result["divided_counts"], str):
                result["divided_counts"] = json.loads(result["divided_counts"])
            result["divided_counts"] = {
                int(index): Counter({
                    int(bits, 2) if isinstance(bits, str) else bits: count
                    for bits, count in result["divided_counts"][index].items()
                })
                for index in result["divided_counts"]
            }

        return OqtopusSamplingResult(result)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusSamplingJob.

        Returns:
            str: A string representation of the OqtopusSamplingJob.

        """
        return self._job.to_str()
