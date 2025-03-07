from quri_parts.circuit import QuantumCircuit
from quri_parts.core.operator import Operator, pauli_label

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusEstimationBackend

circuit = QuantumCircuit(2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)

operator = Operator({
    pauli_label("X 0 X 1"): 1 + 0j,
    pauli_label("Z 0 Z 1"): 1 + 0j,
})

backend = OqtopusEstimationBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.estimate(
    circuit,
    operator=operator,
    device_id="Kawasaki",
    shots=10000,
    name="name",
    description="description",
)
print(job)
estimation = job.result().estimation
print(estimation)
