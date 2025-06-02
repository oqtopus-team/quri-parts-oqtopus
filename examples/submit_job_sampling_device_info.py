from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend, OqtopusDeviceBackend

circuit = QuantumCircuit(2)
circuit.add_H_gate(0)
circuit.add_CNOT_gate(0, 1)

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

# Choose an available device
device_backend = OqtopusDeviceBackend(OqtopusConfig.from_file("oqtopus-dev"))
devices = device_backend.get_devices()
available_devices = []
# filter available devices
for dev in devices:
    if dev.status == "available":
        available_devices.append(dev)
if not available_devices:
    raise RuntimeError("No available device found.")

# select the device with the "least" number of pending jobs
best_device = available_devices[0]
n_pending_jobs = float('inf')
for one_available_device in available_devices:
    if one_available_device.n_pending_jobs < n_pending_jobs:
        best_device = one_available_device
        n_pending_jobs = one_available_device.n_pending_jobs


# Submit the job to the device which is available and has the least number of pending jobs
job = backend.sample(
    circuit,
    device_id=best_device.device_id,
    shots=10000,
)
print(job)
counts = job.result().counts
print(counts)
