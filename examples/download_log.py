from quri_parts_oqtopus.backend import (
    OqtopusConfig,
    OqtopusJobBackendBase,
    OqtopusSseJob,
)

backend = OqtopusJobBackendBase(OqtopusConfig.from_file("oqtopus-dev"))

job_id = "target_job_id"
save_dir = "examples"
job = backend.retrieve_job(job_id)

if isinstance(job, OqtopusSseJob):
    job.download_log(save_dir)
