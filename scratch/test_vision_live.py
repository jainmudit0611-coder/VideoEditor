import os
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.src.services.vision_analyzer import VisionAnalyzerService

# Test using base endpoint
analyzer = VisionAnalyzerService(
    endpoint="https://mudit96jainmj-9810-resource.services.ai.azure.com",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    deployment="gpt-4.1-mini",
    api_version="2024-08-01-preview"
)

# Create a small 1x1 test image or use an extracted frame
import numpy as np
import cv2

dummy_frame_path = "scratch/test_frame.jpg"
img = np.zeros((100, 100, 3), dtype=np.uint8)
cv2.imwrite(dummy_frame_path, img)

print("Calling analyzer.analyze_frame with live Azure OpenAI...")
obs = analyzer.analyze_frame(dummy_frame_path, timestamp=1.5)
print("Vision analysis observations returned:", len(obs))
for o in obs:
    print("  Observation:", o)
