from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

job_id = "target_job_id"
job = backend.retrieve_job(job_id)
job.cancel()
print(job)
