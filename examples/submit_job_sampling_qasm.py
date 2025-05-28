from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend

program = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;

h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.sample_qasm(
    program,
    device_id="Kawasaki",
    shots=10000,
)
print(job)
counts = job.result().counts
print(counts)
