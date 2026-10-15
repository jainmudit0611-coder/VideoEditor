import os
import shutil
import tempfile
import logging
import cv2
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("video-frame-extractor")

class VideoFrame(BaseModel):
    """Container for an extracted keyframe image."""
    timestamp: float = Field(description="Timestamp in seconds from start of video")
    frame_path: str = Field(description="Local filesystem path to extracted JPEG image")
    frame_index: Optional[int] = Field(default=None, description="Frame index number in video sequence")

class VideoFrameExtractorService:
    """
    Extracts representative keyframe images from local video files using OpenCV.
    Implements interval baseline sampling and targeted interest timestamp sampling.
    """
    def __init__(self, interval_seconds: Optional[float] = None):
        env_interval = os.getenv("VIDEO_FRAME_INTERVAL_SECONDS", "5.0")
        try:
            self.interval_seconds = interval_seconds if interval_seconds is not None else float(env_interval)
        except ValueError:
            self.interval_seconds = 5.0

    def extract_frames(
        self,
        video_path: str,
        session_id: str,
        interest_timestamps: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Extracts keyframe JPEG images from a local MP4 video file.
        
        Args:
            video_path: Path to downloaded MP4 file.
            session_id: Unique audit session identifier.
            interest_timestamps: Optional list of specific timestamps (in seconds) to extract.
            
        Returns:
            Dictionary containing session_dir and list of extracted VideoFrame dictionaries.
        """
        if not os.path.exists(video_path):
            logger.warning(f"Video file not found at: {video_path}")
            return {"session_dir": None, "frames": []}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"OpenCV failed to open video file: {video_path}")
            return {"session_dir": None, "frames": []}

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0.0
        
        logger.info(f"Opened Video for Frame Extraction: FPS={fps:.2f}, Frames={total_frames}, Duration={duration:.2f}s")

        # 1. Determine Target Timestamps
        timestamps_set = set()
        
        # Baseline interval sampling (e.g. 0s, 5s, 10s...)
        curr_t = 0.0
        while curr_t <= duration:
            timestamps_set.add(round(curr_t, 2))
            curr_t += self.interval_seconds

        # Add interest timestamps (with +- 1.0s window) if provided
        if interest_timestamps:
            for t in interest_timestamps:
                if 0.0 <= t <= duration:
                    timestamps_set.add(round(max(0.0, t - 1.0), 2))
                    timestamps_set.add(round(t, 2))
                    timestamps_set.add(round(min(duration, t + 1.0), 2))

        # Filter and sort timestamps, maintaining minimum 1.5s separation to avoid redundant frames
        sorted_raw = sorted(list(timestamps_set))
        target_timestamps = []
        last_t = -10.0
        for t in sorted_raw:
            if t - last_t >= 1.5:
                target_timestamps.append(t)
                last_t = t

        # Limit max extracted frames to 20 per session for performance safety
        target_timestamps = target_timestamps[:20]

        # 2. Create Session Directory for Frame JPEGs
        temp_base = tempfile.gettempdir()
        session_dir = os.path.join(temp_base, f"brand_guardian_frames_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        extracted_frames: List[Dict[str, Any]] = []

        # 3. Extract Keyframes
        for idx, t in enumerate(target_timestamps):
            frame_no = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = cap.read()
            if ret:
                frame_filename = f"frame_{t:.1f}s.jpg".replace(".", "_") + ".jpg"
                out_path = os.path.join(session_dir, frame_filename)
                
                # Resize large frames to max 1024px width for efficient storage/vision API input
                height, width = frame.shape[:2]
                if width > 1024:
                    new_height = int(height * (1024 / width))
                    frame = cv2.resize(frame, (1024, new_height), interpolation=cv2.INTER_AREA)

                cv2.imwrite(out_path, frame)
                extracted_frames.append({
                    "timestamp": t,
                    "frame_path": out_path,
                    "frame_index": frame_no
                })

        cap.release()
        logger.info(f"Extracted {len(extracted_frames)} keyframe images into: {session_dir}")

        return {
            "session_dir": session_dir,
            "frames": extracted_frames
        }

    def cleanup_session_frames(self, session_dir: Optional[str]):
        """Safely removes temporary session frame directory and files."""
        if session_dir and os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session frames directory: {session_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup frames directory {session_dir}: {e}")
