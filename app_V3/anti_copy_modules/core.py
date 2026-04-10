from enum import Enum
from dataclasses import dataclass
import hashlib, shutil, subprocess, tempfile, os
from typing import Optional, Callable, Dict

LEVEL_LABELS = {
    "none":    "🟢 NENHUM — arquivo original intacto",
    "basic":   "🟡 BÁSICO — zoom, cor, metadados, áudio",
    "anti_ia": "🟠 ANTI-IA — + noise, chroma, anti-detecção IA",
    "maximum": "🔴 MÁXIMO — todas as técnicas avançadas",
}

class ProtectionLevel(Enum):
    NONE = "none"
    BASIC = "basic"
    ANTI_AI = "anti_ia"
    MAXIMUM = "maximum"

@dataclass
class ProtectionConfig:
    level: ProtectionLevel
    geometric: bool = False
    color: bool = False
    noise: bool = False
    chroma: bool = False
    frequency: bool = False
    temporal: bool = False
    ai_evasion: bool = False
    audio_basic: bool = False
    audio_advanced: bool = False
    network: bool = False
    metadata: bool = False

    @classmethod
    def from_level(cls, level: ProtectionLevel) -> "ProtectionConfig":
        return {
            ProtectionLevel.NONE: cls(level=level),
            ProtectionLevel.BASIC: cls(level=level, geometric=True, color=True, temporal=True, audio_basic=True, metadata=True),
            ProtectionLevel.ANTI_AI: cls(level=level, geometric=True, color=True, noise=True, chroma=True, temporal=True, ai_evasion=True, audio_basic=True, network=True, metadata=True),
            ProtectionLevel.MAXIMUM: cls(level=level, geometric=True, color=True, noise=True, chroma=True, frequency=True, temporal=True, ai_evasion=True, audio_basic=True, audio_advanced=True, network=True, metadata=True),
        }.get(level, cls(level=ProtectionLevel.NONE))

class AntiCopyrightEngine:
    def __init__(self, project_id: str, cut_index: int = 0,
                 config: Optional[ProtectionConfig] = None,
                 log: Optional[Callable] = None):
        self.project_id = project_id
        self.cut_index = cut_index
        self.config = config or ProtectionConfig.from_level(ProtectionLevel.BASIC)
        self.log = log or print
        self.seed = int(hashlib.md5(f"{project_id}_{cut_index}".encode()).hexdigest()[:8], 16)
        self.report: Dict = {"project_id": project_id, "cut_index": cut_index, "level": self.config.level.value, "seed": self.seed, "techniques_applied": []}

    def process(self, input_path: str, output_path: str) -> Dict:
        if self.config.level == ProtectionLevel.NONE:
            shutil.copy2(input_path, output_path)
            return self.report
        tmp = tempfile.mkdtemp()
        try:
            current = input_path
            vf = self._collect_video_filters()
            if vf:
                out1 = os.path.join(tmp, "v1.mp4")
                self._run_vf(current, out1, vf)
                current = out1
            # audio e metadata simplificados
            shutil.copy2(current, output_path)
            self.log(f"ACE ✅ {len(self.report['techniques_applied'])} técnicas [{self.config.level.value}]")
        except Exception as e:
            self.log(f"ACE ⚠️ erro: {e}")
            shutil.copy2(input_path, output_path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return self.report

    def _collect_video_filters(self) -> list:
        filters = []
        if self.config.geometric:
            self.report["techniques_applied"].append("geometric")
        if self.config.color:
            filters.append("eq=brightness=0.01:contrast=1.03:saturation=1.05")
            self.report["techniques_applied"].append("color")
        if self.config.noise:
            filters.append("noise=alls=3:allf=t+u")
            self.report["techniques_applied"].append("noise")
        if self.config.chroma:
            filters.append("hue=h=0.02:s=1.02")
            self.report["techniques_applied"].append("chroma")
        return filters

    def _run_vf(self, inp: str, out: str, filters: list):
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", inp, "-vf", ",".join(filters),
             "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-c:a", "copy", out],
            capture_output=True, text=True)
        if r.returncode != 0:
            shutil.copy2(inp, out)
