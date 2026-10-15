import logging
import time
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

conn_str = "InstrumentationKey=98b597c9-e155-4eb2-afaa-93ac29687d81;IngestionEndpoint=https://eastus2.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus2.livediagnostics.monitor.azure.com/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brand-guardian-appinsights-test")

print("Configuring Azure Monitor with eastus2 connection string...")
try:
    configure_azure_monitor(
        connection_string=conn_str,
        logger_name="brand-guardian-appinsights-test"
    )
    print("configure_azure_monitor initialized successfully!")

    tracer = trace.get_tracer("brand-guardian-tracer")
    with tracer.start_as_current_span("app-insights-live-audit-test") as span:
        span.set_attribute("audit.job_id", "test-job-999")
        span.set_attribute("audit.result", "PASSED")
        logger.info("Emitted live telemetry span to Azure Application Insights (eastus2)")

    # Allow background exporter thread to flush
    time.sleep(3)
    print("Telemetry export flush complete!")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
