from oqtopus_client import rest as client_models
from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.backend.base import OqtopusBackendBase
from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.models.jobs.estimation import OqtopusEstimationJob
from quri_parts_oqtopus.models.jobs.sampling import OqtopusSamplingJob
from quri_parts_oqtopus.models.jobs.sse import OqtopusSseJob


class OqtopusJobBackendBase(OqtopusBackendBase):
    """Base class for OQTOPUS backend jobs.

    Args:
        config: A :class:`OqtopusConfig` for circuit execution.
            If this parameter is ``None`` and both environment variables ``OQTOPUS_URL``
            and ``OQTOPUS_API_TOKEN`` exist, create a :class:`OqtopusConfig` using
            the values of the ``OQTOPUS_URL``, ``OQTOPUS_API_TOKEN``, and
            ``OQTOPUS_PROXY`` environment variables.

            If this parameter is ``None`` and the environment variables do not exist,
            the ``default`` section in the ``~/.oqtopus`` file is read.

    """

    def __init__(self, config: OqtopusConfig | None = None) -> None:
        super().__init__(config)

    def retrieve_job(
        self, job_id: str
    ) -> OqtopusSamplingJob | OqtopusEstimationJob | OqtopusSseJob:
        """Retrieve the job with the given id from OQTOPUS Cloud.

        Args:
            job_id: The id of the job to retrieve.

        Returns:
            The job with the given ``job_id``.

        Raises:
            BackendError: If job cannot be found or if an authentication error occurred,
                etc.

        """
        try:
            response = self._client.get_job(job_id)
        except Exception as e:
            msg = "To retrieve_job from OQTOPUS Cloud is failed."
            raise BackendError(msg) from e

        # check job_type
        if response.job_type == client_models.JobsJobType.SAMPLING:
            return OqtopusSamplingJob(job=response, client=self._client)
        if response.job_type == client_models.JobsJobType.ESTIMATION:
            return OqtopusEstimationJob(job=response, client=self._client)
        if response.job_type == client_models.JobsJobType.MULTI_MANUAL:
            return OqtopusSamplingJob(job=response, client=self._client)
        if response.job_type == client_models.JobsJobType.SSE:
            return OqtopusSseJob(job=response, client=self._client)

        msg = f"Unknown job_type: {response.job_type}"
        raise BackendError(msg)
