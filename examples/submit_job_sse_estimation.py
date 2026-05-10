from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSseBackend

backend = OqtopusSseBackend(OqtopusConfig.from_file("oqtopus-dev"))

job = backend.run_sse(
    file_path="examples/user_program_estimation.py",
    device_id="qulacs",
    name="sse estimation example",
)
print(job)
result = job.result()
print(result.exp_value)
print(result.stds)

job.download_log(
    save_dir="examples",
)
