from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend

circuit = QuantumCircuit(2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

transpiler_info = {
    "transpiler_lib": "qiskit",
    "transpiler_options": {
        "optimization_level": 2,
    },
}

job = backend.sample(
    circuit,
    device_id="Kawasaki",
    shots=10000,
    transpiler_info=transpiler_info,
)
print(job)
counts = job.result().counts
print(counts)
