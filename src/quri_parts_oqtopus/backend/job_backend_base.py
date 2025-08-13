from quri_parts.backend import (
    BackendError,
)

from quri_parts_oqtopus.backend.backend_base import OqtopusBackendBase
from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.backend.data.estimation import OqtopusEstimationJob
from quri_parts_oqtopus.backend.data.sampling import OqtopusSamplingJob
from quri_parts_oqtopus.rest import JobApi, JobsJobDef
from quri_parts_oqtopus.rest.models.jobs_job_type import JobsJobType


class OqtopusJobBackendBase(OqtopusBackendBase):
    """Base class for oqtopus job backend.

    This class extends :class:`OqtopusBackendBase` and provides additional functionality
    specific to job management in the Oqtopus backend.

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
        self._job_api: JobApi = JobApi(api_client=self._api_client)

    def retrieve_job(self, job_id: str) -> OqtopusSamplingJob | OqtopusEstimationJob:
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
            response = self._job_api.get_job(job_id)
        except Exception as e:
            msg = "To retrieve_job from OQTOPUS Cloud is failed."
            raise BackendError(msg) from e

        # check if response is a valid job definition
        if not isinstance(response, JobsJobDef):
            msg = "The response from OQTOPUS Cloud is not a valid job definition."
            raise BackendError(msg)

        # check job_type
        if response.job_type is JobsJobType.SAMPLING:
            return OqtopusSamplingJob(job=response, job_api=self._job_api)
        if response.job_type is JobsJobType.ESTIMATION:
            return OqtopusEstimationJob(job=response, job_api=self._job_api)
        if response.job_type is JobsJobType.SSE:
            msg = "SSE job is not supported in this backend."
            raise BackendError(msg)

        msg = f"Unknown job_type: {response.job_type}"
        raise BackendError(msg)
