import json
from collections import Counter
from typing import Any

from quri_parts.backend import (
    BackendError,
    SamplingCounts,
    SamplingResult,
)

from quri_parts_oqtopus.backend.data.job_base import OqtopusJobBase
from quri_parts_oqtopus.rest import (
    JobApi,
    JobsJobDef,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusSamplingResult(SamplingResult):
    """A result of a sampling job.

    Args:
        result: A result of dict type.
            This dict should have the key ``counts``.
            The value of ``counts`` is the dict input for the counts.
            Where the keys represent a measured classical value
            and the value is an integer the number of shots with that result.

            If the keys of ``counts`` is expressed as a bit string,
            then ``properties`` is a mapping from the index of bit string
            to the index of the quantum circuit.

    Raises:
        ValueError: If ``counts`` does not exist in result.

    Examples:
        An example of a dict of result is as below:

        .. code-block::

            {
                "counts": {
                    "0": 600,
                    "1": 300,
                    "3": 100,
                }
            }

        In the above case, the bit string representation of 0, 1, and 3
        in the keys of ``counts`` is "00", "01", and "11" respectively.
        The LSB (Least Significant Bit) of the bit string representation is
        ``classical index``=0.

    """

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__()

        if "counts" not in result:
            msg = "'counts' does not exist in result"
            raise ValueError(msg)

        self._result = result
        self._counts: SamplingCounts = Counter(result.get("counts"))
        self._divided_counts: dict[str, SamplingCounts] | None = None
        if result.get("divided_counts"):
            self._divided_counts = {
                index: Counter({
                    int(bits): count
                    for bits, count in result["divided_counts"][index].items()
                })
                for index in result["divided_counts"]
            }

    @property
    def counts(self) -> SamplingCounts:
        """Returns the dict input for the counts."""
        return self._counts

    @property
    def divided_counts(self) -> dict | None:
        """Returns divided_counts."""
        return self._divided_counts

    def __repr__(self) -> str:
        """Return a string representation.

        Returns:
            str: A string representation.

        """
        return str(self._result)


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
