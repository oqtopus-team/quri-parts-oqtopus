from quri_parts.core.operator import Operator, pauli_label

from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusEstimationBackend

program = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

operator = Operator({
    pauli_label("X0 X1"): 1,
    pauli_label("Z0 Z1"): 1,
})

backend = OqtopusEstimationBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.estimate_qasm(
    program,
    operator=operator,
    device_id="Kawasaki",
    shots=10000,
)
print(job)
result = job.result()
print(result.exp_value)
print(result.stds)
