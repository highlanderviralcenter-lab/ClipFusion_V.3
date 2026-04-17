"""
Engine de corte e renderização para o ClipFusion V3.

Implementa uma renderização em duas passagens com detecção de VA‑API.
Caso VA‑API não esteja disponível, recorre ao libx264.  Também
permite adicionar legendas SRT simples e realizar dublagem via gTTS
(quando disponível).  Este módulo utiliza ffmpeg para todas as
operações de mídia.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def _detect_vaapi() -> bool:
    """Detecta se VA‑API está disponível no sistema."""
    return os.environ.get("LIBVA_DRIVER_NAME") is not None

def _build_srt(segments: List[Tuple[float, float]], texts: List[str], srt_path: str) -> None:
    """Gera um arquivo SRT simples a partir de tempos e textos."""
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, ((start, end), text) in enumerate(zip(segments, texts), start=1):
            # Converte segundos para hh:mm:ss,ms
            def fmt(ts: float) -> str:
                hrs = int(ts // 3600)
                mins = int((ts % 3600) // 60)
                secs = ts % 60
                return f"{hrs:02}:{mins:02}:{secs:06.3f}".replace('.', ',')
            f.write(f"{idx}\n{fmt(start)} --> {fmt(end)}\n{text}\n\n")

def _prepare_dub_audio(text: str, lang: str, out_path: str) -> bool:
    """Gera áudio dublado via gTTS se disponível."""
    try:
        from gtts import gTTS  # type: ignore
        tts = gTTS(text=text, lang=lang)
        tts.save(out_path)
        return True
    except Exception:
        return False

def _replace_audio(video_path: str, audio_path: str, output_path: str) -> None:
    """Substitui a faixa de áudio de um vídeo."""
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", output_path
    ], check=True)

def render_cut(
    video_path: str,
    start: float,
    end: float,
    transcript: str,
    plan: Dict[str, bool],
    platform: str,
    output_path: str,
) -> None:
    """Renderiza um corte de vídeo com base nos parâmetros fornecidos.

    Esta função realiza:
    * Corte do vídeo no intervalo [start, end]
    * Renderização com VA‑API quando possível e fallback para x264
    * Adição de legendas
    * Dublagem opcional (quando gTTS disponível e activado no plano)
    """
    # Primeiro corta o vídeo
    with tempfile.TemporaryDirectory() as tmpdir:
        clip_path = Path(tmpdir) / "clip.mp4"
        cmd_cut = [
            "ffmpeg", "-y", "-i", video_path, "-ss", str(start), "-to", str(end),
            "-c:v", "copy", "-c:a", "copy", str(clip_path),
        ]
        subprocess.run(cmd_cut, check=True)
        # Monta comando de encode
        vaapi = _detect_vaapi()
        vcodec = "hevc_vaapi" if vaapi else "libx264"
        acodec = "copy"
        intermediate = Path(tmpdir) / "encoded.mp4"
        cmd_encode = [
            "ffmpeg", "-y", "-i", str(clip_path),
            "-c:v", vcodec,
            "-c:a", acodec,
            "-vf", "format=nv12" if vaapi else "null",
            str(intermediate),
        ]
        subprocess.run(cmd_encode, check=True)
        # Cria legenda simples a partir de transcript inteiro
        srt = Path(tmpdir) / "out.srt"
        # Usa um único bloco para todo o corte
        _build_srt([(0.0, end - start)], [transcript], str(srt))
        # Adiciona legenda ao vídeo
        with_subs = Path(tmpdir) / "with_subs.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(intermediate), "-vf", f"subtitles={srt}",
            "-c:v", "copy", "-c:a", "copy", str(with_subs)
        ], check=True)
        final_vid = with_subs
        # Se o plano pedir dublagem, tenta gerar e substituir
        if plan.get("audio_advanced"):
            dub = Path(tmpdir) / "dub.mp3"
            if _prepare_dub_audio(transcript, "pt", str(dub)):
                out_dubbed = Path(tmpdir) / "dubbed.mp4"
                _replace_audio(str(with_subs), str(dub), str(out_dubbed))
                final_vid = out_dubbed
        # Copia para destino
        subprocess.run(["ffmpeg", "-y", "-i", str(final_vid), "-c", "copy", output_path], check=True)
