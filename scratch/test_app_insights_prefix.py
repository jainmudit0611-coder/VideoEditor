import os
from dotenv import load_dotenv

conn_str = "InstrumentationKey=98b597c9-e155-4eb2-afaa-93ac29687d81"
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(connection_string=conn_str)
    print("InstrumentationKey= prefix accepted!")
except Exception as e:
    print(f"Failed with prefix: {type(e).__name__}: {e}")
