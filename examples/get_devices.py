from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusDeviceBackend

# create backend
backend = OqtopusDeviceBackend(OqtopusConfig.from_file("oqtopus-dev"))
# get the device list
devices = backend.get_devices()

# print the device list
for dev in devices:
    print(f"### device for {dev.device_id}")
    print(dev.to_json())
    print(dev.device_type)
    print(dev.status)
    print(dev.available_at)
    print(dev.n_pending_jobs)
    print(dev.basis_gates)
    print(dev.supported_instructions)
    print(dev.device_info)
    print(dev.calibrated_at)
    print(dev.description)
