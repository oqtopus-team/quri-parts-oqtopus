from collections.abc import Iterable
from itertools import starmap
from typing import TYPE_CHECKING, Optional, TypeVar

from quri_parts.circuit import ImmutableQuantumCircuit
from quri_parts.core.sampling import ConcurrentSampler, MeasurementCounts
from quri_parts.core.utils.concurrent import execute_concurrently
from quri_parts.openqasm.circuit import convert_to_qasm_str

from quri_parts_oqtopus.backend import OqtopusSamplingBackend

T_common = TypeVar("T_common")
T_individual = TypeVar("T_individual")
R = TypeVar("R")

if TYPE_CHECKING:
    from concurrent.futures import Executor

backend = OqtopusSamplingBackend()


# MeasurementCounts and SamplingCounts are equivalent
def _sample(circuit: ImmutableQuantumCircuit, shots: int) -> MeasurementCounts:
    qasm = convert_to_qasm_str(circuit)
    job = backend.sample_qasm(qasm, shots=shots)
    return job.result().counts


def _sample_sequentially(
    _: object, circuit_shots_tuples: Iterable[tuple[ImmutableQuantumCircuit, int]]
) -> Iterable[MeasurementCounts]:
    return list(starmap(_sample, circuit_shots_tuples))


def _sample_concurrently(
    circuit_shots_tuples: Iterable[tuple[ImmutableQuantumCircuit, int]],
    executor: Optional["Executor"],
    concurrency: int = 1,
) -> Iterable[MeasurementCounts]:
    return execute_concurrently(
        _sample_sequentially, None, circuit_shots_tuples, executor, concurrency
    )


def create_oqtopus_concurrent_sampler(
    executor: Optional["Executor"] = None, concurrency: int = 1
) -> ConcurrentSampler:
    """Create `ConcurrentSampler` for executing quantum circuits.

    Args:
        executor (Optional[&quot;Executor&quot;], optional): `Executor`
            for executing quantum circuits. Defaults to None.
        concurrency (int, optional): The number of concurrency. Defaults to 1.

    Returns:
        ConcurrentSampler: `ConcurrentSampler` for executing quantum circuits.

    """

    def sampler(
        circuit_shots_tuples: Iterable[tuple[ImmutableQuantumCircuit, int]],
    ) -> Iterable[MeasurementCounts]:
        return _sample_concurrently(circuit_shots_tuples, executor, concurrency)

    return sampler
