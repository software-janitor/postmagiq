"""GPU detection for Ollama model tier selection."""

import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUInfo:
    """Information about detected GPU."""

    vendor: str  # "nvidia", "amd", "apple", "none"
    vram_gb: float
    name: Optional[str] = None


def detect_gpu() -> GPUInfo:
    """Detect available GPU and VRAM.

    Tries in order:
    1. NVIDIA via nvidia-smi
    2. AMD via rocm-smi
    3. Apple Metal via sysctl (macOS only)

    Returns GPUInfo with vendor="none" if no GPU detected.
    """
    # Try NVIDIA first (most common for ML)
    nvidia = _detect_nvidia()
    if nvidia:
        return nvidia

    # Try AMD
    amd = _detect_amd()
    if amd:
        return amd

    # Try Apple Metal (macOS only)
    if platform.system() == "Darwin":
        apple = _detect_apple_metal()
        if apple:
            return apple

    return GPUInfo(vendor="none", vram_gb=0.0)


def _detect_nvidia() -> Optional[GPUInfo]:
    """Detect NVIDIA GPU using nvidia-smi.

    Parses output format: "GeForce RTX 3090, 24576" (name, memory in MB)
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                # Handle multiple GPUs - take the first one
                first_line = output.split("\n")[0]
                parts = first_line.split(",")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    vram_mb = float(parts[1].strip())
                    return GPUInfo(vendor="nvidia", vram_gb=vram_mb / 1024, name=name)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
        pass
    return None


def _detect_amd() -> Optional[GPUInfo]:
    """Detect AMD GPU using rocm-smi.

    Parses VRAM from rocm-smi --showmeminfo vram output.
    """
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Look for "Total Memory (B):" pattern
            match = re.search(r"Total Memory \(B\):\s+(\d+)", result.stdout)
            if match:
                vram_bytes = int(match.group(1))
                return GPUInfo(vendor="amd", vram_gb=vram_bytes / (1024**3))

            # Alternative: try to parse GB directly if format changed
            match = re.search(r"(\d+)\s*GB", result.stdout, re.IGNORECASE)
            if match:
                vram_gb = float(match.group(1))
                return GPUInfo(vendor="amd", vram_gb=vram_gb)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _detect_apple_metal() -> Optional[GPUInfo]:
    """Detect Apple Silicon unified memory.

    On Apple Silicon, GPU shares system RAM. We estimate ~70% is usable
    for GPU tasks based on typical usage patterns.
    """
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            total_bytes = int(result.stdout.strip())
            # Apple Silicon shares RAM; estimate ~70% available for GPU
            gpu_available = (total_bytes / (1024**3)) * 0.7
            return GPUInfo(vendor="apple", vram_gb=gpu_available, name="Apple Silicon")
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def get_model_tier(gpu_info: GPUInfo) -> str:
    """Determine model tier based on VRAM.

    Tiers are defined in workflow_config.yaml with these ranges:
    - tier_cpu: 0-6 GB (or no GPU)
    - tier_8gb: 6-10 GB
    - tier_16gb: 12-18 GB
    - tier_24gb: 20-26 GB
    - tier_48gb: 40+ GB
    """
    vram = gpu_info.vram_gb

    if vram >= 40:
        return "tier_48gb"
    elif vram >= 20:
        return "tier_24gb"
    elif vram >= 12:
        return "tier_16gb"
    elif vram >= 6:
        return "tier_8gb"
    else:
        return "tier_cpu"


def get_gpu_summary() -> dict:
    """Get a summary of GPU detection results.

    Useful for diagnostics and display.
    """
    gpu = detect_gpu()
    tier = get_model_tier(gpu)

    return {
        "vendor": gpu.vendor,
        "vram_gb": round(gpu.vram_gb, 1),
        "name": gpu.name,
        "tier": tier,
        "has_gpu": gpu.vendor != "none",
    }
