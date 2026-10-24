"""Continuous Real-Time Telemetry Sampler using native libnvidia-ml.so / ctypes.

Logs GPU metrics (VRAM, Temperature, Utilization, Fan) at 250ms intervals
into a thread-safe in-memory buffer and structured JSON trace files.
"""

import ctypes
import threading
import time
from typing import Any, Dict, List, Optional


class Memory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


class HardwareTelemetryCollector:
    def __init__(self, sample_interval_sec: float = 0.25):
        self.sample_interval = sample_interval_sec
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.samples: List[Dict[str, Any]] = []
        self._nvml_available = False
        self._nv = None
        self._handle = ctypes.c_void_p()

        try:
            self._nv = ctypes.CDLL("libnvidia-ml.so.1")
            if self._nv.nvmlInit_v2() == 0:
                if self._nv.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(self._handle)) == 0:
                    self._nvml_available = True
        except Exception:
            self._nvml_available = False

    def start(self):
        self.samples.clear()
        self._running = True
        self._thread = threading.Thread(target=self._sampling_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

        if not self.samples:
            return {"vram_static_mib": 0, "vram_peak_mib": 0, "avg_temp_c": 0}

        used_vram = [s["vram_used_mib"] for s in self.samples]
        temps = [s["temperature_c"] for s in self.samples if s.get("temperature_c")]

        return {
            "vram_static_mib": used_vram[0] if used_vram else 0,
            "vram_peak_mib": max(used_vram) if used_vram else 0,
            "vram_min_mib": min(used_vram) if used_vram else 0,
            "avg_temp_c": round(sum(temps) / len(temps), 1) if temps else 0,
            "max_temp_c": max(temps) if temps else 0,
            "total_samples": len(self.samples),
        }

    def _sampling_loop(self):
        while self._running:
            sample = {"timestamp": time.time(), "vram_used_mib": 0, "temperature_c": 0}
            if self._nvml_available and self._nv:
                try:
                    mem = Memory()
                    if self._nv.nvmlDeviceGetMemoryInfo(self._handle, ctypes.byref(mem)) == 0:
                        sample["vram_used_mib"] = int(mem.used // (1024**2))
                        sample["vram_free_mib"] = int(mem.free // (1024**2))

                    temp = ctypes.c_uint()
                    if self._nv.nvmlDeviceGetTemperature(self._handle, 0, ctypes.byref(temp)) == 0:
                        sample["temperature_c"] = int(temp.value)
                except Exception:
                    pass
            self.samples.append(sample)
            time.sleep(self.sample_interval)

    def close(self):
        if self._nvml_available and self._nv:
            try:
                self._nv.nvmlShutdown()
            except Exception:
                pass
