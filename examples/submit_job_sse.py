from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSseJob

backend = OqtopusSseJob(OqtopusConfig.from_file("qiqb-prod"))
# backend = OqtopusSseJob(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.run_sse(
    file_path="examples/user_program.py",
    device_id="Kawasaki",
    name="sse example",
)
print(job)
counts = job.result().counts
print(counts)

backend.download_log(
    job_id=job.job_id,
    save_path="examples",
)
