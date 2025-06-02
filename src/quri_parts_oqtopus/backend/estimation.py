import json
import os
import time
from datetime import datetime
from typing import Any

from quri_parts.backend import BackendError
from quri_parts.circuit import NonParametricQuantumCircuit
from quri_parts.core.operator import Operator
from quri_parts.openqasm.circuit import convert_to_qasm_str

from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.backend.utils import DateTimeEncoder
from quri_parts_oqtopus.rest import (
    ApiClient,
    Configuration,
    JobApi,
    JobsJobDef,
    JobsOperatorItem,
    JobsSubmitJobInfo,
    JobsSubmitJobRequest,
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


class OqtopusEstimationJob:  # noqa: PLR0904
    """A job for a estimation.

    Args:
        job: A result of dict type.
        job_api: A result of dict type.

    Raises:
        ValueError: If ``job`` or ``job_api`` is None.

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
        if self._job.transpiler_info:
            return json.loads(self._job.transpiler_info)
        return {}

    @property
    def simulator_info(self) -> dict:
        """The simulator info of the job.

        Returns:
            dict: The simulator info of the job.

        """
        if self._job.simulator_info:
            return json.loads(self._job.simulator_info)
        return {}

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
        """Return a json string representation of the OqtopusEstimationJob.

        Returns:
            str: A json string representation of the OqtopusEstimationJob.

        """
        return json.dumps(self._job.to_dict(), cls=DateTimeEncoder)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusEstimationJob.

        Returns:
            str: A string representation of the OqtopusEstimationJob.

        """
        return self._job.to_str()


class OqtopusEstimationBackend:
    """A OQTOPUS backend for a estimation.

    Args:
        config: A :class:`OqtopusConfig` for circuit execution.
            If this parameter is ``None`` and both environment variables ``OQTOPUS_URL``
            and ``OQTOPUS_API_TOKEN`` exist, create a :class:`OqtopusConfig` using
            the values of the ``OQTOPUS_URL``, ``OQTOPUS_API_TOKEN``, and
            ``OQTOPUS_PROXY`` environment variables.

            If this parameter is ``None`` and the environment variables do not exist,
            the ``default`` section in the ``~/.oqtopus`` file is read.

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

        # construct JobApi
        rest_config = Configuration()
        rest_config.host = config.url
        if config.proxy:
            rest_config.proxy = config.proxy
        api_client = ApiClient(
            configuration=rest_config,
            header_name="q-api-token",
            header_value=config.api_token,
        )
        self._job_api: JobApi = JobApi(api_client=api_client)

    def estimate(  # noqa: PLR0917, PLR0913
        self,
        program: NonParametricQuantumCircuit,
        operator: Operator,
        device_id: str,
        shots: int,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict | None = None,
        simulator_info: dict | None = None,
        mitigation_info: dict | None = None,
    ) -> OqtopusEstimationJob:
        """Execute a estimation of a circuit.

        The circuit is transpiled on OQTOPUS Cloud.
        The QURI Parts transpiling feature is not supported.
        The circuit is converted to OpenQASM 3.0 format and sent to OQTOPUS Cloud.

        Args:
            program (NonParametricQuantumCircuit): The circuit to be estimated.
            operator (Operator): The observable operator applied to the circuit.
            device_id (str): The device id to be executed.
            shots (int): Number of repetitions of each circuit, for estimation.
            name (str | None, optional): The name to be assigned to the job.
                Defaults to None.
            description (str | None, optional): The description to be assigned to
                the job. Defaults to None.
            transpiler_info (dict | None, optional): The transpiler information.
                Defaults to None.
            simulator_info (dict | None, optional): The simulator information.
                Defaults to None.
            mitigation_info (dict | None, optional): The mitigation information.
                Defaults to None.

        Returns:
            The job to be executed.

        """
        if isinstance(program, list):
            qasm = [convert_to_qasm_str(c) for c in program]
        else:
            qasm = convert_to_qasm_str(program)

        return self.estimate_qasm(
            program=qasm,
            operator=operator,
            device_id=device_id,
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info,
            simulator_info=simulator_info,
            mitigation_info=mitigation_info,
        )

    def estimate_qasm(  # noqa: PLR0913, PLR0917
        self,
        program: str,
        operator: Operator,
        device_id: str,
        shots: int,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict | None = None,
        simulator_info: dict | None = None,
        mitigation_info: dict | None = None,
    ) -> OqtopusEstimationJob:
        """Execute estimation of the program.

        The program is transpiled on OQTOPUS Cloud.
        QURI Parts OQTOPUS does not support QURI Parts transpiling feature.

        Args:
            program (str): The program to be estimated.
            operator (Operator): The observable operator applied to the circuit.
            device_id (str): The device id to be executed.
            shots (int): Number of repetitions of each circuit, for estimation.
            name (str | None, optional): The name to be assigned to the job.
                Defaults to None.
            description (str | None, optional): The description to be assigned to
                the job. Defaults to None.
            transpiler_info (dict | None, optional): The transpiler information.
                Defaults to None.
            simulator_info (dict | None, optional): The simulator information.
                Defaults to None.
            mitigation_info (dict | None, optional): The mitigation information.
                Defaults to None.

        Returns:
            OqtopusEstimationJob: The job to be executed.

        Raises:
            ValueError: If ``shots`` is not a positive integer.
            ValueError: Imaginary part of coefficient is not supported.
            BackendError: If job is wrong or if an authentication error occurred, etc.

        """
        if not shots >= 1:
            msg = f"shots should be a positive integer.: {shots}"
            raise ValueError(msg)

        job_type = "estimation"

        if transpiler_info is None:
            transpiler_info = {}
        if simulator_info is None:
            simulator_info = {}
        if mitigation_info is None:
            mitigation_info = {}

        operator_list = []
        for pauli, coeff in operator.items():
            if isinstance(coeff, complex):
                if coeff.imag != 0.0:
                    msg = f"Complex numbers are not supported in coefficient: {coeff}"
                    raise ValueError(msg)
                operator_list.append(
                    JobsOperatorItem(
                        pauli=str(pauli),
                        coeff=float(coeff.real),
                    )
                )
            else:
                operator_list.append(
                    JobsOperatorItem(
                        pauli=str(pauli),
                        coeff=float(coeff),
                    )
                )
        job_info = JobsSubmitJobInfo(program=[program], operator=operator_list)
        body = JobsSubmitJobRequest(
            name=name,
            description=description,
            device_id=device_id,
            job_type=job_type,
            job_info=job_info,
            transpiler_info=transpiler_info,
            simulator_info=simulator_info,
            mitigation_info=mitigation_info,
            shots=shots,
        )
        try:
            response_submit_job = self._job_api.submit_job(body=body)
            response = self._job_api.get_job(response_submit_job.job_id)
        except Exception as e:
            msg = "To execute estimation on OQTOPUS Cloud is failed."
            raise BackendError(msg) from e

        return OqtopusEstimationJob(response, self._job_api)

    def retrieve_job(self, job_id: str) -> OqtopusEstimationJob:
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

        return OqtopusEstimationJob(response, self._job_api)
