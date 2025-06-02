from quri_parts_oqtopus.backend import OqtopusConfig, OqtopusDeviceBackend
import json

# create backend
backend = OqtopusDeviceBackend(OqtopusConfig.from_file("oqtopus-dev"))
# get the device list
devices = backend.get_devices()

# print the device list
for dev in devices:
    print(f"######## device for {dev.device_id}")
    for key, value in json.loads(dev.to_json()).items():
        print(f"{key}: {value}")
    print("########\n")
