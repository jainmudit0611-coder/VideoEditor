import os
import time
import logging
from typing import Dict, Any, Optional
import requests
import yt_dlp
from azure.identity import DefaultAzureCredential

from backend.src.config import settings
from backend.src.observability import get_logger

logger = get_logger("video-indexer")


_UNSET = object()


class VideoIndexerService:
    """
    Client service for Azure Video Indexer (VI) API.
    Handles ARM token acquisition, VI account token exchange, video uploads, polling, and temporal transcript/OCR extraction.
    Includes configuration validation, timeouts, sanitized error handling, and observable fallback state.
    """
    def __init__(
        self,
        account_id: Any = _UNSET,
        location: Any = _UNSET,
        subscription_id: Any = _UNSET,
        resource_group: Any = _UNSET,
        vi_name: Any = _UNSET,
        timeout: Optional[float] = None,
    ):
        self.account_id = (getattr(settings, "AZURE_VI_ACCOUNT_ID", None) or os.getenv("AZURE_VI_ACCOUNT_ID")) if account_id is _UNSET else account_id
        self.location = (getattr(settings, "AZURE_VI_LOCATION", None) or os.getenv("AZURE_VI_LOCATION")) if location is _UNSET else location
        self.subscription_id = (getattr(settings, "AZURE_SUBSCRIPTION_ID", None) or os.getenv("AZURE_SUBSCRIPTION_ID")) if subscription_id is _UNSET else subscription_id
        self.resource_group = (getattr(settings, "AZURE_RESOURCE_GROUP", None) or os.getenv("AZURE_RESOURCE_GROUP")) if resource_group is _UNSET else resource_group
        self.vi_name = (getattr(settings, "AZURE_VI_NAME", "project-brand-guardian-001") or os.getenv("AZURE_VI_NAME", "project-brand-guardian-001")) if vi_name is _UNSET else vi_name
        self.timeout = timeout if timeout is not None else getattr(settings, "AZURE_VI_TIMEOUT_SECONDS", 30.0)
        self._credential = None

    @property
    def credential(self):
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    @property
    def is_configured(self) -> bool:
        """Returns True if all required Azure Video Indexer credentials and IDs are configured."""
        return bool(self.account_id and self.location and self.subscription_id and self.resource_group)

    def validate_config(self) -> Dict[str, str]:
        """
        Validates Azure Video Indexer configuration safely without exposing secrets.
        Returns a dictionary summarizing credential status.
        """
        return {
            "status": "configured" if self.is_configured else "blocked_by_credentials",
            "account_id": "configured" if bool(self.account_id) else "missing",
            "location": self.location or "missing",
            "subscription_id": "configured" if bool(self.subscription_id) else "missing",
            "resource_group": "configured" if bool(self.resource_group) else "missing",
            "vi_name": self.vi_name or "missing",
            "timeout_seconds": str(self.timeout)
        }

    def get_access_token(self) -> str:
        """Generates an ARM Access Token."""
        if not self.is_configured:
            raise RuntimeError("Azure Video Indexer is unconfigured (BLOCKED_BY_CREDENTIALS). Missing ARM subscription or resource group.")
        try:
            token_object = self.credential.get_token("https://management.azure.com/.default")
            return token_object.token
        except Exception as e:
            logger.error(f"Failed to acquire Azure ARM Token: {e}")
            raise RuntimeError(f"Azure ARM authentication failed: {e}")

    def get_account_token(self, arm_access_token: str) -> str:
        """Exchanges ARM token for Video Indexer Account Token."""
        if not self.is_configured:
            raise RuntimeError("Azure Video Indexer is unconfigured (BLOCKED_BY_CREDENTIALS).")

        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.vi_name}"
            f"/generateAccessToken?api-version=2024-01-01"
        )
        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType": "Contributor", "scope": "Account"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if response.status_code == 401 or response.status_code == 403:
                raise RuntimeError(f"Azure Video Indexer account access denied (HTTP {response.status_code}).")
            if response.status_code == 429:
                raise RuntimeError("Azure Video Indexer rate limit exceeded (HTTP 429).")
            if response.status_code != 200:
                raise RuntimeError(f"Failed to acquire VI Account Token (HTTP {response.status_code}).")
            return response.json().get("accessToken")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Azure Video Indexer token exchange timed out after {self.timeout}s.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Azure Video Indexer network error: {e}")

    def download_youtube_video(self, url: str, output_path: str = "temp_video.mp4") -> str:
        """Downloads a YouTube video to a local file using yt-dlp."""
        logger.info(f"Downloading video from URL: {url}")
        ydl_opts = {
            "format": "best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            logger.info("Video download complete.")
            return output_path
        except Exception as e:
            raise Exception(f"YouTube Download Failed: {str(e)}")

    def upload_video(self, video_path: str, video_name: str) -> str:
        """Uploads a local media file to Azure Video Indexer."""
        if not self.is_configured:
            raise RuntimeError("Azure Video Indexer is unconfigured (BLOCKED_BY_CREDENTIALS). Cannot upload video.")

        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)

        api_url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"
        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "indexingPreset": "Default",
        }

        logger.info(f"Uploading file {video_path} to Azure Video Indexer...")
        try:
            with open(video_path, "rb") as video_file:
                files = {"file": video_file}
                response = requests.post(api_url, params=params, files=files, timeout=self.timeout)

            if response.status_code == 401 or response.status_code == 403:
                raise RuntimeError(f"Azure Video Indexer upload authorization failed (HTTP {response.status_code}).")
            if response.status_code == 429:
                raise RuntimeError("Azure Video Indexer upload rate limited (HTTP 429).")
            if response.status_code != 200:
                raise RuntimeError(f"Azure Video Indexer upload failed (HTTP {response.status_code}).")

            video_id = response.json().get("id")
            if not video_id:
                raise RuntimeError("Azure Video Indexer upload response missing video id.")
            return video_id
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Azure Video Indexer upload timed out after {self.timeout}s.")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Azure Video Indexer upload network error: {e}")

    def wait_for_processing(self, video_id: str, max_wait_seconds: int = 300, poll_interval_seconds: int = 5) -> Dict[str, Any]:
        """Polls processing status until complete or timed out."""
        if not self.is_configured:
            raise RuntimeError("Azure Video Indexer is unconfigured (BLOCKED_BY_CREDENTIALS).")

        logger.info(f"Waiting for video {video_id} indexing to complete...")
        t_start = time.time()

        while (time.time() - t_start) < max_wait_seconds:
            arm_token = self.get_access_token()
            vi_token = self.get_account_token(arm_token)

            url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos/{video_id}/Index"
            params = {"accessToken": vi_token}
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                if response.status_code != 200:
                    raise RuntimeError(f"Azure Video Indexer status check failed (HTTP {response.status_code}).")

                data = response.json()
                state = data.get("state")
                if state == "Processed":
                    logger.info(f"Video {video_id} processing completed successfully.")
                    return data
                elif state == "Failed":
                    raise RuntimeError("Azure Video Indexing Failed in Azure.")
                elif state == "Quarantined":
                    raise RuntimeError("Azure Video Quarantined (Copyright / Content Policy Violation).")

                logger.info(f"Indexing status: {state}... waiting {poll_interval_seconds}s")
                time.sleep(poll_interval_seconds)
            except requests.exceptions.Timeout:
                logger.warning("Polling request timed out; will retry on next loop.")
                time.sleep(poll_interval_seconds)

        raise TimeoutError(f"Azure Video Indexer processing exceeded max wait time of {max_wait_seconds}s.")

    def _parse_time(self, time_str: str) -> float:
        """Converts time string (e.g., '0:01:23.45' or '00:12') to seconds float."""
        try:
            parts = str(time_str).split(":")
            if len(parts) == 3:
                return round(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2]), 2)
            elif len(parts) == 2:
                return round(float(parts[0]) * 60 + float(parts[1]), 2)
            return round(float(parts[0]), 2)
        except Exception:
            return 0.0

    def extract_data(self, vi_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parses raw VI JSON into structured state items with timestamps."""
        transcript_lines = []
        transcript_items = []
        for v in vi_json.get("videos", []):
            for insight in v.get("insights", {}).get("transcript", []):
                text = insight.get("text")
                if text:
                    transcript_lines.append(text)
                    instances = insight.get("instances", [])
                    start_t = 0.0
                    end_t = 0.0
                    if instances and isinstance(instances, list):
                        start_t = self._parse_time(instances[0].get("start", "0:00:00"))
                        end_t = self._parse_time(instances[0].get("end", "0:00:00"))
                    transcript_items.append({
                        "text": text,
                        "start_time": start_t,
                        "end_time": end_t,
                        "speaker": insight.get("speakerId", "Unknown")
                    })

        ocr_lines = []
        ocr_items = []
        for v in vi_json.get("videos", []):
            for insight in v.get("insights", {}).get("ocr", []):
                text = insight.get("text")
                if text:
                    ocr_lines.append(text)
                    instances = insight.get("instances", [])
                    start_t = 0.0
                    end_t = 0.0
                    if instances and isinstance(instances, list):
                        start_t = self._parse_time(instances[0].get("start", "0:00:00"))
                        end_t = self._parse_time(instances[0].get("end", "0:00:00"))
                    ocr_items.append({
                        "text": text,
                        "start_time": start_t,
                        "end_time": end_t
                    })

        return {
            "transcript": " ".join(transcript_lines),
            "ocr_text": ocr_lines,
            "transcript_items": transcript_items,
            "ocr_items": ocr_items,
            "video_metadata": {
                "duration": vi_json.get("summarizedInsights", {}).get("duration", {}).get("seconds"),
                "platform": "youtube"
            }
        }