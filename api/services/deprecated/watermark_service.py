"""Service for removing watermarks from images using LaMA inpainting.

Calls the watermark service container via HTTP to avoid
importing PyTorch in the main orchestrator container.
"""

import base64
import os
from pathlib import Path
from typing import Optional

import httpx

# Service URL from environment or default
WATERMARK_SERVICE_URL = os.environ.get("WATERMARK_SERVICE_URL", "http://localhost:8001")


class WatermarkService:
    """Service for removing watermarks from images via HTTP."""

    def __init__(self, service_url: Optional[str] = None, timeout: float = 120.0):
        self.service_url = service_url or WATERMARK_SERVICE_URL
        self.timeout = timeout

    def is_available(self) -> dict:
        """Check if watermark removal service is available."""
        try:
            response = httpx.get(
                f"{self.service_url}/status",
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
            return {"available": False, "error": f"Status code: {response.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def remove_watermark(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        use_lama: bool = True,
    ) -> dict:
        """Remove watermark from an image file.

        Args:
            input_path: Path to the input image
            output_path: Path for the output image (optional)
            use_lama: Ignored (always uses LaMA via service)

        Returns:
            Dict with status, output_path, and optionally base64 image_data
        """
        input_path = Path(input_path)
        if not input_path.exists():
            return {"success": False, "error": f"Input file not found: {input_path}"}

        # Default output path
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
        else:
            output_path = Path(output_path)

        # Determine output format from extension
        ext = output_path.suffix.lower()
        output_format = "png"
        if ext in (".jpg", ".jpeg"):
            output_format = "jpg"
        elif ext == ".webp":
            output_format = "webp"

        try:
            # Read input file
            with open(input_path, "rb") as f:
                file_content = f.read()

            # Call watermark service
            response = httpx.post(
                f"{self.service_url}/remove",
                files={"file": (input_path.name, file_content)},
                data={"output_format": output_format},
                timeout=self.timeout,
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Service error: {response.status_code}",
                }

            result = response.json()
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                }

            # Decode base64 and save to output path
            image_data = result["image_data"]
            image_bytes = base64.b64decode(image_data)

            with open(output_path, "wb") as f:
                f.write(image_bytes)

            return {
                "success": True,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "image_data": image_data,  # Also return base64 for DB storage
                "method": "lama",
            }

        except httpx.TimeoutException:
            return {"success": False, "error": "Watermark removal timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_watermark_bytes(
        self,
        image_bytes: bytes,
        filename: str = "image.png",
        output_format: str = "png",
    ) -> dict:
        """Remove watermark from image bytes (for uploads).

        Args:
            image_bytes: Raw image bytes
            filename: Original filename for content type detection
            output_format: Output format (png, jpg, webp)

        Returns:
            Dict with success status and base64 image_data
        """
        try:
            response = httpx.post(
                f"{self.service_url}/remove",
                files={"file": (filename, image_bytes)},
                data={"output_format": output_format},
                timeout=self.timeout,
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Service error: {response.status_code}",
                }

            result = response.json()
            return result

        except httpx.TimeoutException:
            return {"success": False, "error": "Watermark removal timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_watermark_batch(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        use_lama: bool = True,
    ) -> dict:
        """Remove watermarks from all images in a directory.

        Args:
            input_dir: Directory containing images
            output_dir: Output directory (default: same as input)
            use_lama: Ignored (always uses LaMA)

        Returns:
            Dict with results for each file
        """
        input_dir = Path(input_dir)
        if not input_dir.is_dir():
            return {"success": False, "error": f"Directory not found: {input_dir}"}

        output_dir = Path(output_dir) if output_dir else input_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        extensions = {".png", ".jpg", ".jpeg", ".webp"}
        results = []

        for img_path in input_dir.iterdir():
            if img_path.suffix.lower() in extensions:
                out_path = output_dir / f"{img_path.stem}_clean{img_path.suffix}"
                result = self.remove_watermark(str(img_path), str(out_path))
                results.append(result)

        return {
            "success": True,
            "processed": len(results),
            "results": results,
        }
