from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend

circuit1 = QuantumCircuit(2)
circuit1.add_H_gate(0)
circuit1.add_CNOT_gate(0, 1)

circuit2 = QuantumCircuit(1)
circuit2.add_X_gate(0)

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.sample(
    [circuit1, circuit2],
    device_id="Kawasaki",
    shots=10000,
)
print(job)
counts = job.result().divided_counts
print(counts)
