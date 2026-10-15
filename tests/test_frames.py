import sys
import os
import unittest
import tempfile
import numpy as np
import cv2

sys.path.insert(0, r"C:\Users\IngenxT\AppData\Roaming\Python\Python313\site-packages")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.src.services.video_frames import VideoFrameExtractorService

class TestVideoFramesService(unittest.TestCase):
    def setUp(self):
        # Create a synthetic 2-second video for testing OpenCV extraction
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = os.path.join(self.temp_dir, "test_synth.mp4")
        
        height, width = 480, 640
        fps = 30.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.video_path, fourcc, fps, (width, height))
        
        for _ in range(60):  # 60 frames = 2 seconds
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            out.write(frame)
        out.release()

    def tearDown(self):
        if os.path.exists(self.video_path):
            os.remove(self.video_path)
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_extract_frames_synthetic(self):
        service = VideoFrameExtractorService(interval_seconds=1.0)
        res = service.extract_frames(self.video_path, "session_test", interest_timestamps=[0.5, 1.5])
        
        session_dir = res.get("session_dir")
        frames = res.get("frames", [])
        
        self.assertIsNotNone(session_dir)
        self.assertTrue(len(frames) >= 1)
        self.assertTrue(os.path.exists(frames[0]["frame_path"]))
        
        # Cleanup test
        service.cleanup_session_frames(session_dir)
        self.assertFalse(os.path.exists(session_dir))

if __name__ == "__main__":
    unittest.main()
