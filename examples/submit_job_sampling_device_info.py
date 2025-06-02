from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend, OqtopusDeviceBackend

circuit = QuantumCircuit(2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

# Choose an available device
device_backend = OqtopusDeviceBackend(OqtopusConfig.from_file("oqtopus-dev"))
devices = device_backend.get_devices()
available_device = None
for dev in devices:
    if dev.status == "available":
        available_device = dev
        break
if available_device is None:
    raise RuntimeError("No available device found.")

# Submit the job to the available device
job = backend.sample(
    circuit,
    device_id=available_device.device_id,
    shots=10000,
)
print(job)
counts = job.result().counts
print(counts)
