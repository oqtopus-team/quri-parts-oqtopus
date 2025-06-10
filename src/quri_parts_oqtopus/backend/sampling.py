"""A module to execute sampling on OQTOPUS Cloud.

Before sampling, sign up for OQTOPUS Cloud and create a configuration file in
path ``~/.oqtopus``. See the description of :meth:`OqtopusConfig.from_file` method
for how to write ``~/.oqtopus`` file.

Examples:
    To execute sampling 1000 shots on OQTOPUS Cloud, run the following code:

    .. highlight:: python
    .. code-block:: python

        from quri_parts.circuit import QuantumCircuit
        from quri_parts_oqtopus.backend import OqtopusSamplingBackend

        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)

        backend = OqtopusSamplingBackend()
        job = backend.sample(circuit, n_shots=1000)
        counts = job.result().counts
        print(counts)

    To execute with the transpiler setting on OQTOPUS Cloud, run the following code:

    .. highlight:: python
    .. code-block:: python

        from quri_parts.circuit import QuantumCircuit
        from quri_parts_oqtopus.backend import OqtopusSamplingBackend

        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)

        backend = OqtopusSamplingBackend()
        job = backend.sample(circuit, n_shots=10000, transpiler="normal")
        counts = job.result().counts
        print(counts)

    The specifications of the transpiler setting is as follows:

    - ``"none"``: no transpiler
    - ``"pass"``: use the "do nothing transpiler" (same as ``"none"``)
    - ``"normal"``: use default transpiler (by default)

    You can also input OpenQASM 3.0 program.

    .. highlight:: python
    .. code-block:: python

        from quri_parts.circuit import QuantumCircuit
        from quri_parts_oqtopus.backend import OqtopusSamplingBackend

        qasm = \"\"\"OPENQASM 3;
        include "stdgates.inc";
        qubit[2] q;

        h q[0];
        cx q[0], q[1];\"\"\"

        backend = OqtopusSamplingBackend()
        job = backend.sample_qasm(qasm, n_shots=1000)
        counts = job.result().counts
        print(counts)

    To retrieve jobs already sent to OQTOPUS Cloud, run the following code:

    .. highlight:: python
    .. code-block:: python

        from quri_parts_oqtopus.backend import OqtopusSamplingBackend

        job = backend.retrieve_job("<put target job id>")
        counts = job.result().counts
        print(counts)

"""

import json
import os
import time
from collections import Counter
from datetime import datetime
from typing import Any

from quri_parts.backend import (
    BackendError,
    SamplingCounts,
    SamplingJob,
    SamplingResult,
)
from quri_parts.circuit import NonParametricQuantumCircuit
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
    JobsSubmitJobInfo,
    JobsSubmitJobRequest,
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


class OqtopusSamplingJob(SamplingJob):  # noqa: PLR0904
    """A job for a sampling measurement.

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
        """Return a json string representation of the OqtopusSamplingJob.

        Returns:
            str: A json string representation of the OqtopusSamplingJob.

        """
        return json.dumps(self._job.to_dict(), cls=DateTimeEncoder)

    def __repr__(self) -> str:
        """Return a string representation of the OqtopusSamplingJob.

        Returns:
            str: A string representation of the OqtopusSamplingJob.

        """
        return self._job.to_str()


class OqtopusSamplingBackend:
    """A OQTOPUS backend for a sampling measurement.

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

    def sample(  # noqa: PLR0917, PLR0913
        self,
        program: NonParametricQuantumCircuit | list[NonParametricQuantumCircuit],
        device_id: str,
        shots: int,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict | None = None,
        simulator_info: dict | None = None,
        mitigation_info: dict | None = None,
    ) -> OqtopusSamplingJob:
        """Execute a sampling measurement of a circuit.

        The circuit is transpiled on OQTOPUS Cloud.
        The QURI Parts transpiling feature is not supported.
        The circuit is converted to OpenQASM 3.0 format and sent to OQTOPUS Cloud.

        Args:
            program (NonParametricQuantumCircuit | list[NonParametricQuantumCircuit]):
                The circuit to be sampled.
            device_id (str): The device id to be executed.
            shots (int): Number of repetitions of each circuit, for sampling.
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
        qasm: str | list[str]
        if isinstance(program, list):
            qasm = [_convert_to_qasm_str_with_measure(c) for c in program]
        else:
            qasm = _convert_to_qasm_str_with_measure(program)

        return self.sample_qasm(
            program=qasm,
            device_id=device_id,
            shots=shots,
            name=name,
            description=description,
            transpiler_info=transpiler_info,
            simulator_info=simulator_info,
            mitigation_info=mitigation_info,
        )

    def sample_qasm(  # noqa: PLR0913, PLR0917
        self,
        program: str | list[str],
        device_id: str,
        shots: int,
        name: str | None = None,
        description: str | None = None,
        transpiler_info: dict | None = None,
        simulator_info: dict | None = None,
        mitigation_info: dict | None = None,
        job_type: str | None = None,
    ) -> OqtopusSamplingJob:
        """Execute sampling measurement of the program.

        The program is transpiled on OQTOPUS Cloud.
        QURI Parts OQTOPUS does not support QURI Parts transpiling feature.

        Args:
            program (str | list[str]): The program to be sampled.
            device_id (str): The device id to be executed.
            shots (int): Number of repetitions of each circuit, for sampling.
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
            job_type (str | None, optional): The job type. Defaults to None.

        Returns:
            OqtopusSamplingJob: The job to be executed.

        Raises:
            ValueError: If ``shots`` is not a positive integer.
            BackendError: If job is wrong or if an authentication error occurred, etc.

        """
        if not shots >= 1:
            msg = f"shots should be a positive integer.: {shots}"
            raise ValueError(msg)

        if job_type is None:
            if isinstance(program, list):
                job_type = "multi_manual"
            else:
                job_type = "sampling"
                program = [program]

        if transpiler_info is None:
            transpiler_info = {}
        if simulator_info is None:
            simulator_info = {}
        if mitigation_info is None:
            mitigation_info = {}

        try:
            if os.getenv("OQTOPUS_ENV") == "sse_container":
                # This section is only for inside SSE container.
                import sse_sampler  # type: ignore[import-not-found]  # noqa: PLC0415

                response = sse_sampler.req_transpile_and_exec(
                    program, shots, transpiler_info
                )
                job = OqtopusSamplingJob(response, self._job_api)
                # Workaround to avoid thread pool closing error when destructor of
                # _job_api. Anyway the job_api cannot be used in SSE container.
                del job._job_api  # noqa: SLF001
            else:
                job_info = JobsSubmitJobInfo(program=program)
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
                response_submit_job = self._job_api.submit_job(body=body)
                response = self._job_api.get_job(response_submit_job.job_id)
                job = OqtopusSamplingJob(response, self._job_api)
        except Exception as e:
            msg = "To execute sampling on OQTOPUS Cloud is failed."
            raise BackendError(msg) from e

        return job

    def retrieve_job(self, job_id: str) -> OqtopusSamplingJob:
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

        return OqtopusSamplingJob(response, self._job_api)


def _convert_to_qasm_str_with_measure(program: NonParametricQuantumCircuit) -> str:
    qasm = convert_to_qasm_str(program)
    # If `qasm` does not contain "measure",
    # then add the bit declaration and append "measure"
    if "measure" not in qasm:
        # declare bits
        qubit_index = qasm.find("qubit")
        if qubit_index != -1:
            semicolon_index = qasm.find(";", qubit_index)
            if semicolon_index != -1:
                size = program.qubit_count
                declare_bit = f"\nbit[{size}] c;"
                qasm = (
                    qasm[: semicolon_index + 1]
                    + declare_bit
                    + qasm[semicolon_index + 1 :]
                )
        # append measure
        qasm += "\nc = measure q;"
    return qasm
