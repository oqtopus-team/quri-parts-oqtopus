from quri_parts.circuit import QuantumCircuit
from quri_parts.core.operator import Operator, pauli_label

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusEstimationBackend

circuit = QuantumCircuit(2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)

operator = Operator({
    pauli_label("X0 X1"): 1,
    pauli_label("Z0 Z1"): 1,
})

backend = OqtopusEstimationBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.estimate(
    circuit,
    operator=operator,
    device_id="Kawasaki",
    shots=10000,
)
print(job)
result = job.result()
print(result.exp_value)
print(result.stds)
