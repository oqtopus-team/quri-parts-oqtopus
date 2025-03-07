from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusSamplingBackend

backend = OqtopusSamplingBackend(OqtopusConfig.from_file("oqtopus-dev"))

job_id = "target_job_id"
job = backend.retrieve_job(job_id)

# print job
print("### job")
print(job.to_json())
print(job.job_id)
print(job.name)
print(job.description)
print(job.job_type)
print(job.status)
print(job.device_id)
print(job.shots)
print("### job_info")
print(f"job_info={job.job_info}")  # dict
if job.job_info:
    print(f"program={job.job_info['program']}")
    if "transpile_result" in job.job_info:
        print(
            f"transpiled_program={job.job_info['transpile_result']['transpiled_program']}"
        )
        print(f"stats={job.job_info['transpile_result']['stats']}")
        print(
            f"virtual_physical_mapping={job.job_info['transpile_result']['virtual_physical_mapping']}"
        )
    print(f"message={job.job_info['message']}")
print("### transpiler_info")
print(job.transpiler_info)  # dict
print("### simulator_info")
print(job.simulator_info)  # dict
print("### mitigation_info")
print(job.mitigation_info)  # dict
print(job.submitted_at)
print(job.ready_at)
print(job.running_at)
print(job.ended_at)

# print result
if job.status != "succeeded":
    exit(0)

result = job.result()
print(f"### result({job.job_type})")
print(result)

if job.job_type == "sampling":
    print(result.counts)
    print(result.counts[0])
    print(result.divided_counts)

if job.job_type == "estimation":
    print(result.estimation["exp_value"])
    print(result.estimation["stds"])
    print(result.transpile_result)
