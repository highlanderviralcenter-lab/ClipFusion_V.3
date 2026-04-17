"""
Transcritor de áudio/vídeo para o ClipFusion V3.

Utiliza Whisper ou faster‑whisper quando disponível para gerar
transcrições.  Em ambientes sem estas bibliotecas, retorna um
texto fictício para permitir que o pipeline continue.
"""
import os
import tempfile
import subprocess
from typing import Dict, List, Tuple

class WhisperTranscriber:
    def __init__(self, model_size: str = "base", use_faster: bool = True) -> None:
        self.model_size = model_size
        self.use_faster = use_faster

    def _extract_audio(self, video_path: str, out_path: str) -> None:
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", out_path
        ], check=True)

    def transcribe(self, video_path: str, language: str = "pt") -> Dict[str, any]:
        try:
            # Tenta usar faster_whisper
            if self.use_faster:
                from faster_whisper import WhisperModel  # type: ignore
                model = WhisperModel(self.model_size)
                # Converte vídeo em áudio temporário
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    self._extract_audio(video_path, tmp.name)
                    segments, info = model.transcribe(tmp.name, language=language)
                    text = "".join(s[2] for s in segments)
                return {"text": text.strip(), "segments": []}
            else:
                raise ImportError
        except ImportError:
            try:
                import whisper  # type: ignore
                model = whisper.load_model(self.model_size)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    self._extract_audio(video_path, tmp.name)
                    result = model.transcribe(tmp.name, language=language)
                return {"text": result.get("text", "").strip(), "segments": result.get("segments", [])}
            except Exception:
                return {"text": "Transcrição fictícia: conte o conteúdo do vídeo manualmente.", "segments": []}
