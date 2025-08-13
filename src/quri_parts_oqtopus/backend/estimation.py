from quri_parts.backend import BackendError
from quri_parts.circuit import NonParametricQuantumCircuit
from quri_parts.core.operator import Operator
from quri_parts.openqasm.circuit import convert_to_qasm_str

from quri_parts_oqtopus.backend.config import (
    OqtopusConfig,
)
from quri_parts_oqtopus.backend.data.estimation import OqtopusEstimationJob
from quri_parts_oqtopus.backend.job_backend_base import OqtopusJobBackendBase
from quri_parts_oqtopus.rest import (
    JobsOperatorItem,
    JobsSubmitJobInfo,
    JobsSubmitJobRequest,
)

JOB_FINAL_STATUS = ["succeeded", "failed", "cancelled"]


class OqtopusEstimationBackend(OqtopusJobBackendBase):
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
        super().__init__(config=config)

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
