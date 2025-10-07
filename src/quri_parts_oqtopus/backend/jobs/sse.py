"""A module to run sse job on OQTOPUS Cloud."""

import base64
from pathlib import Path, PurePath

from quri_parts.backend import BackendError

from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.backend.jobs.base import OqtopusJobBackendBase
from quri_parts_oqtopus.backend.jobs.sampling import OqtopusSamplingBackend
from quri_parts_oqtopus.models.jobs.sse import OqtopusSseJob


class OqtopusSseBackend(OqtopusJobBackendBase):
    """A job for a SSE.

    Args:
        config: A :class:`OqtopusConfig` for job execution.

    """

    def __init__(self, config: OqtopusConfig | None = None) -> None:
        super().__init__(config=config)

    def run_sse(
        self,
        file_path: str,
        device_id: str,
        name: str,
        description: str | None = None,
    ) -> OqtopusSseJob:
        """Perform a SSE job.

        Args:
            file_path (str): The path to program file to upload.
            device_id (str): The identifier of the device where the job is executed.
            name (str): The name of the job.
            description (str | None, optional): The description of the job.
                Defaults to None.

        Raises:
            ValueError: If ``file_path`` is not set.
            ValueError: If ``file_path`` does not exist.
            ValueError: If ``file_path`` is not a python file.
            ValueError: If file size is larger than max file size
            BackendError: If an error is returned from OQTOPUS Cloud.

        Returns:
            OqtopusSseJob: The job to be executed.

        """
        # if file_path is not set, raise ValueError
        if file_path is None:
            msg = "file_path is not set."
            raise ValueError(msg)

        # if the file does not exist, raise ValueError
        if not Path(file_path).exists():
            msg = f"The file does not exist: {file_path}"
            raise ValueError(msg)

        # get the base name and the extension of the file
        ext = PurePath(file_path).suffix

        # if the extension is not .py, raise ValueError
        if ext != ".py":
            msg = f"The file is not python file: {file_path}"
            raise ValueError(msg)

        with Path(file_path).open(mode="rb") as f:
            encoded = base64.b64encode(f.read())

        max_file_size = 10 * 1024 * 1024  # 10MB

        # if the file size is larger than max_file_size, raise ValueError
        if len(encoded) >= max_file_size:
            msg = f"size of the base64 encoded file is larger than {max_file_size}"
            raise ValueError(msg)

        try:
            backend = OqtopusSamplingBackend(self.config)
            job = backend.sample_qasm(
                program=[encoded.decode("utf-8")],
                shots=1,
                name=name,
                device_id=device_id,
                description=description,
                job_type="sse",
            )
        except Exception as e:
            msg = "To perform sse on OQTOPUS Cloud is failed."
            raise BackendError(msg) from e

        return OqtopusSseJob(job=job._job, job_api=job._job_api)  # noqa: SLF001
