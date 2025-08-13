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

import os

from quri_parts.backend import (
    BackendError,
)
from quri_parts.circuit import NonParametricQuantumCircuit
from quri_parts.openqasm.circuit import convert_to_qasm_str

from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.backend.data.sampling import OqtopusSamplingJob
from quri_parts_oqtopus.backend.job_backend_base import OqtopusJobBackendBase
from quri_parts_oqtopus.rest import (
    JobsSubmitJobInfo,
    JobsSubmitJobRequest,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusSamplingBackend(OqtopusJobBackendBase):
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
        super().__init__(config=config)

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
