from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSseBackend

backend = OqtopusSseBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.run_sse(
    file_path="examples/user_program.py",
    device_id="qulacs",
    name="sse example",
)
print(job)
counts = job.result().counts
print(counts)

job.download_log(
    save_dir="examples",
)
