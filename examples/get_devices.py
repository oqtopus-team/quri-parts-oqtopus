from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusDeviceBackend

# create backend
backend = OqtopusDeviceBackend(OqtopusConfig.from_file("oqtopus-dev"))
# get the device list
devices = backend.get_devices()

# print the device list
for dev in devices:
    print(f"######## device for {dev.device_id}")
    print(f"to_json(): {dev.to_json()}")
    print(f"device_id: {dev.device_type}")
    print(f"status: {dev.status}")
    print(f"available_at: {dev.available_at}")
    print(f"n_pending_jobs: {dev.n_pending_jobs}")
    print(f"basis_gates: {dev.basis_gates}")
    print(f"supported_instructions: {dev.supported_instructions}")
    print(f"device_info: {dev.device_info}") # dict
    print(f"calibrated_at: {dev.calibrated_at}")
    print(f"description: {dev.description}")
