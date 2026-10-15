import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

ikey = "98b597c9-e155-4eb2-afaa-93ac29687d81"

regions = [
    "westus3",
    "westus2",
    "eastus",
    "eastus2",
    "centralus",
    "southcentralus",
    "northcentralus",
    "westus",
    "westeurope",
    "northeurope"
]

endpoints = [
    ("global_dc", "https://dc.services.visualstudio.com/v2/track"),
    ("global_in", "https://dc.applicationinsights.azure.com/v2/track")
]
for r in regions:
    endpoints.append((r, f"https://{r}.in.applicationinsights.azure.com/v2/track"))

body = [{
    "name": "Microsoft.ApplicationInsights.Message",
    "time": datetime.now(timezone.utc).isoformat(),
    "iKey": ikey,
    "data": {
        "baseType": "MessageData",
        "baseData": {
            "ver": 2,
            "message": "Brand Guardian Connectivity Verification Ping",
            "severityLevel": "Information"
        }
    }
}]

payload = json.dumps(body).encode("utf-8")

print(f"Testing App Insights endpoints with iKey: {ikey[:8]}...")
for name, url in endpoints:
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            print(f"[{name}] {url} -> HTTP {response.status}: {res_body}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        print(f"[{name}] {url} -> HTTP {e.code}: {err_body[:100]}")
    except Exception as e:
        print(f"[{name}] {url} -> {type(e).__name__}: {e}")
