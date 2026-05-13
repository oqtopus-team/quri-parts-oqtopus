import time

from oqtopus_client import OqtopusClient, OqtopusConfig, OqtopusJobSpec

for index in range(3):
    time.sleep(1)
    print(f"## Start iteration {index} ##")
    program = """OPENQASM 3;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c = measure q;
"""

    client = OqtopusClient(OqtopusConfig(base_url=""))
    result = client.run_sampling(
        OqtopusJobSpec.sampling(
            device_id="sse",
            shots=1000,
            program=program,
        )
    )
    print(f"result.job_id={result.job_id}")
    print(result.get_counts())

print("## Finish ##")
