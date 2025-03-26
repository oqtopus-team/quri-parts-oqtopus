from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSseBackend

backend = OqtopusSseBackend(OqtopusConfig.from_file("oqtopus-dev"))

job_id = "target_job_id"
save_dir = "examples"
backend.download_log(
    job_id=job_id,
    save_dir=save_dir,
)
