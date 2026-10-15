import os
import base64
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.src.graph.state import VisualObservation
from backend.src.config import settings
from backend.src.observability import (
    log_event,
    ObservabilityEvent,
    get_logger,
)

logger = get_logger("vision-analyzer")


class VisionAnalysisResult(BaseModel):
    """Structured response container for visual observations per keyframe."""
    observations: List[VisualObservation] = Field(
        description="Structured visual observations identified in the keyframe"
    )


_UNSET = object()


class VisionAnalyzerService:
    """
    Performs multimodal vision analysis on extracted keyframe images using Azure OpenAI.
    Extracts structured visual observations regarding disclosures, branding, CTAs, and disclaimers.
    Includes timeouts, controlled retries, sanitized error handling, and observable degraded OCR fallback.
    """
    def __init__(
        self,
        endpoint: Any = _UNSET,
        api_key: Any = _UNSET,
        deployment: Any = _UNSET,
        api_version: Any = _UNSET,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        raw_endpoint = (getattr(settings, "AZURE_OPENAI_ENDPOINT", None) or os.getenv("AZURE_OPENAI_ENDPOINT")) if endpoint is _UNSET else endpoint
        if raw_endpoint:
            from urllib.parse import urlparse
            parsed = urlparse(raw_endpoint)
            if parsed.netloc and parsed.path and parsed.path != "/":
                self.endpoint = f"{parsed.scheme}://{parsed.netloc}"
            else:
                self.endpoint = raw_endpoint
        else:
            self.endpoint = None

        self.api_key = (getattr(settings, "AZURE_OPENAI_API_KEY", None) or os.getenv("AZURE_OPENAI_API_KEY")) if api_key is _UNSET else api_key
        default_deployment = (
            getattr(settings, "AZURE_OPENAI_CHAT_DEPLOYMENT", None)
            or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
            or getattr(settings, "AZURE_OPENAI_DEPLOYMENT", None)
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            or "gpt-4o"
        )
        self.deployment = default_deployment if deployment is _UNSET else deployment
        default_version = getattr(settings, "AZURE_OPENAI_API_VERSION", "2024-08-01-preview") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        self.api_version = default_version if api_version is _UNSET else api_version
        self.timeout = timeout if timeout is not None else getattr(settings, "AZURE_OPENAI_TIMEOUT_SECONDS", 30.0)
        self.max_retries = max_retries if max_retries is not None else getattr(settings, "AZURE_OPENAI_MAX_RETRIES", 2)
        self.last_error_reason: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """Returns True if all required Azure OpenAI Vision credentials are present and non-empty."""
        return bool(self.api_key and self.endpoint)

    def validate_config(self) -> Dict[str, str]:
        """
        Validates Azure OpenAI configuration safely without exposing secrets.
        Returns a dictionary summarizing credential status and operational mode.
        """
        return {
            "status": "configured" if self.is_configured else "blocked_by_credentials",
            "endpoint": "configured" if bool(self.endpoint) else "missing",
            "api_key": "configured" if bool(self.api_key) else "missing",
            "deployment": "configured" if bool(self.deployment) else "missing",
            "api_version": self.api_version or "missing",
            "timeout_seconds": str(self.timeout),
            "max_retries": str(self.max_retries),
            "fallback_mode": "DEGRADED_OCR_FALLBACK" if not self.is_configured else "NATIVE_VISION"
        }

    def encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encodes local JPEG image file to base64 data string."""
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None

    def analyze_frame(self, frame_path: str, timestamp: float) -> List[Dict[str, Any]]:
        """
        Analyzes a single keyframe image for visual compliance evidence using Azure OpenAI.
        
        Args:
            frame_path: Local path to keyframe JPEG image.
            timestamp: Keyframe timestamp in seconds.
            
        Returns:
            List of visual observation dictionaries, or empty list on failure / unconfigured state.
        """
        if not self.is_configured:
            self.last_error_reason = "UNCONFIGURED_CREDENTIALS"
            logger.info("Azure OpenAI vision unconfigured (BLOCKED_BY_CREDENTIALS). Skipping native vision inference.")
            return []

        base64_img = self.encode_image_to_base64(frame_path)
        if not base64_img:
            return []

        try:
            llm = AzureChatOpenAI(
                azure_deployment=self.deployment,
                openai_api_version=self.api_version,
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                temperature=0.0,
                request_timeout=self.timeout,
                max_retries=self.max_retries,
            )

            structured_vision = llm.with_structured_output(VisionAnalysisResult)

            system_prompt = """
            You are a Computer Vision Compliance Auditor. Analyze the provided video keyframe image.
            Identify any visual compliance evidence:
            1. Disclosure text (e.g. #ad, #sponsored, Paid Partnership, Advertisement).
            2. Brand logos or product packaging.
            3. On-screen CTAs (e.g. Buy Now, Use Code, Link in Bio).
            4. Fine print disclaimers or legal text overlays.
            
            Return structured observations stating category, description, exact visible text snippet if present, visibility status, and confidence score.
            """

            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            }

            user_message = [
                {"type": "text", "text": f"Keyframe Image at timestamp {timestamp:.1f} seconds:"},
                image_content
            ]

            result: VisionAnalysisResult = structured_vision.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])

            observations = []
            for obs in result.observations:
                obs_dict = obs.model_dump()
                obs_dict["timestamp"] = timestamp
                obs_dict["frame_path"] = frame_path
                obs_dict["mode"] = "NATIVE_VISION"
                observations.append(obs_dict)

            self.last_error_reason = None
            return observations

        except Exception as e:
            err_str = str(e)
            # Classify error safely without echoing secrets
            if "401" in err_str or "unauthorized" in err_str.lower() or "invalid_api_key" in err_str.lower():
                self.last_error_reason = "AUTH_FAILURE"
                logger.warning(f"Azure OpenAI vision authentication failed (HTTP 401/403) at timestamp {timestamp:.1f}s.")
            elif "429" in err_str or "rate_limit" in err_str.lower():
                self.last_error_reason = "RATE_LIMITED"
                logger.warning(f"Azure OpenAI vision rate limit exceeded (HTTP 429) at timestamp {timestamp:.1f}s.")
            elif "timeout" in err_str.lower() or "timed out" in err_str.lower():
                self.last_error_reason = "TIMEOUT"
                logger.warning(f"Azure OpenAI vision request timed out after {self.timeout}s at timestamp {timestamp:.1f}s.")
            else:
                self.last_error_reason = "PROVIDER_ERROR"
                logger.warning(f"Azure OpenAI vision request failed at timestamp {timestamp:.1f}s: {type(e).__name__}.")

            return []

    def analyze_batch_frames(
        self,
        frames: List[Dict[str, Any]],
        ocr_items: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[List[Dict[str, Any]], bool]:
        """
        Analyzes a batch of extracted keyframes, incorporating OCR items as pseudo-visual fallback if needed.
        
        Returns:
            Tuple of (all_observations_list, is_degraded_mode_boolean)
        """
        all_observations = []
        is_degraded = False

        # Attempt native vision analysis if credentials configured
        if self.is_configured:
            for frame_item in frames:
                path = frame_item.get("frame_path")
                t = frame_item.get("timestamp", 0.0)
                if path and os.path.exists(path):
                    obs_list = self.analyze_frame(path, t)
                    all_observations.extend(obs_list)

        # If unconfigured or native vision yielded no observations due to provider issues, activate degraded mode
        if not self.is_configured or self.last_error_reason is not None:
            is_degraded = True

        # Fallback: Construct pseudo-visual observations from OCR timestamp items
        if not all_observations and ocr_items:
            is_degraded = True
            logger.info("Vision analysis running in DEGRADED_OCR_FALLBACK mode: utilizing on-screen OCR evidence.")
            for item in ocr_items:
                text = item.get("text", "")
                t = item.get("start_time", 0.0)
                category = "disclosure" if any(k in text.lower() for k in ["#ad", "sponsor", "paid", "promotion"]) else "branding"
                all_observations.append({
                    "timestamp": t,
                    "category": category,
                    "description": f"On-screen visual OCR text (DEGRADED BACKUP): '{text}'",
                    "text": text,
                    "text_snippet": text,
                    "is_prominent": True,
                    "confidence": 0.85,
                    "mode": "DEGRADED_OCR_FALLBACK"
                })

        return all_observations, is_degraded
