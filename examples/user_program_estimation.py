import time
import traceback

from quri_parts.circuit import QuantumCircuit
from quri_parts.core.operator import Operator, pauli_label

from quri_parts_oqtopus.backend import OqtopusEstimationBackend

for index in range(3):
    time.sleep(1)
    print(f"## Start iteration {index} ##")
    try:
        circuit = QuantumCircuit(2)
        circuit.add_H_gate(0)
        circuit.add_CNOT_gate(0, 1)

        operator = Operator({
            pauli_label("X0 X1"): 1,
            pauli_label("Z0 Z1"): 1,
        })

        job = OqtopusEstimationBackend().estimate(
            circuit,
            shots=1000,
            device_id="sse",
            operator=operator
        )
        print(f"{job.job_id=}")
        result = job.result()
        print(f"{result.exp_value}")
        print(f"{result.stds}")

    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()

print("## Finish ##")
