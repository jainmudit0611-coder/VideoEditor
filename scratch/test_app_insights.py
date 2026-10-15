import os
from dotenv import load_dotenv

load_dotenv(override=True)

conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
print("APPLICATIONINSIGHTS_CONNECTION_STRING:", conn_str)

try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(connection_string=conn_str)
    print("configure_azure_monitor success!")
except Exception as e:
    print(f"configure_azure_monitor failed: {type(e).__name__}: {e}")
