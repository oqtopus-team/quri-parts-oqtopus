from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSseJob

backend = OqtopusSseJob(OqtopusConfig.from_file("oqtopus-dev"))

job_id = "target_job_id"
save_path = "examples"
backend.download_log(
    job_id=job_id,
    save_path=save_path,
)
