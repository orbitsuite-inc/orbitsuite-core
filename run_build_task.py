from src.supervisor import Supervisor
sv = Supervisor()
res = sv.process_request("Create a simple Python calculator that prints results and produce an executable exe")
import json, os, pprint # type: ignore
pipe = res.get("result",{}).get("result",{}).get("pipeline_artifacts",{})
print("Pipeline artifacts partial: ")
print(json.dumps(pipe, indent=2))
print("Done")
