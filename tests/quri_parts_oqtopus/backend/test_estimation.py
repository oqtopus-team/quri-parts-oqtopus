import json

import pytest
from oqtopus_client import OqtopusClient
from oqtopus_client import OqtopusConfig as ClientConfig
from oqtopus_client.services.job_results import OqtopusEstimationJobResult

from quri_parts_oqtopus.models.jobs.estimation import OqtopusEstimationJob


def test_estimation_result_keeps_mitigation_details():
    mitigation_details = {
        "ro_error_mitigation": {
            "method": "local_readout_mitigation",
            "raw_counts": None,
            "quasi_probabilities": None,
            "expectation_values": [
                {
                    "pauli": "X 0 X 1",
                    "coefficient": 1.5,
                    "before_expectation_value": 0.8,
                    "after_expectation_value": 1.0,
                    "standard_deviation_upper_bound": 0.04,
                }
            ],
        }
    }
    job_raw = OqtopusEstimationJobResult(
        job_id="estimation-rem",
        name="estimation-rem",
        job_type="estimation",
        status="succeeded",
        device_id="qulacs",
        shots=100,
        job_info={
            "program": ["OPENQASM 3;"],
            "result": {
                "estimation": {"exp_value": 1.0, "stds": 0.1},
                "mitigation_details": mitigation_details,
            },
        },
    )
    client = OqtopusClient(
        ClientConfig(base_url="dummy_url", api_token="dummy_token")  # noqa: S106
    )
    job = OqtopusEstimationJob(job=job_raw, client=client)

    assert job.mitigation_details is not None
    assert json.loads(job.mitigation_details) == mitigation_details
    result = job.result()
    assert result.exp_value == pytest.approx(1.0)
    assert result.mitigation_details == job.mitigation_details
