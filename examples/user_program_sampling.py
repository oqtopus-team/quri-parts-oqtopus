import time
import traceback

from quri_parts.circuit import QuantumCircuit

from quri_parts_oqtopus.backend import OqtopusSamplingBackend

for index in range(3):
    time.sleep(1)
    print(f"## Start iteration {index} ##")
    try:
        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)
        mitigation_info = {
            "ro_error_mitigation": "pseudo_inverse",
        }

        job = OqtopusSamplingBackend().sample(
            circuit,
            shots=1000,
            device_id="sse",
            mitigation_info=mitigation_info,
        )
        print(f"{job.job_id=}")
        result = job.result()
        print(f"{result.counts}")

    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()

print("## Finish ##")
