"""
Pipeline híbrido do ClipFusion V3.

Fluxo:
1) cria projeto no banco
2) extrai/limpa áudio
3) transcreve
4) segmenta (transcrição + pausas como fallback)
5) rankeia candidatos por heurísticas de retenção/plataforma
6) renderiza cortes aprovados
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Callable, Dict, Tuple

from ..infra.db import (
    create_project,
    save_transcription,
    save_candidate,
    save_cut,
    update_cut_status,
    update_cut_output,
)
from .audio_processor import AudioProcessor
from .transcriber import WhisperTranscriber
from .segment import segment_by_pauses
from .cut_engine import render_cut
from .decision_engine import evaluate_decision
from .prompt_builder import build_external_ai_prompt, parse_ai_response, normalize_external_ai_response
from ..viral_engine.platform_optimizer import platform_fit_score
from ..viral_engine.hook_engine import ViralHookEngine


def build_plan(level: str):
    """
    Tenta usar factory externa (se existir no tree), e faz fallback local.
    """
    try:
        from ..anti_copy_modules.protection_factory import build_plan as external_build_plan
        return external_build_plan(level)
    except Exception:
        pass

    level = (level or "none").lower()
    plans = {
        "none": {},
        "basic": {"geometric": True, "color": True, "temporal": True, "metadata": True},
        "anti_ia": {"geometric": True, "color": True, "temporal": True, "metadata": True, "noise": True, "chroma": True},
        "maximum": {"geometric": True, "color": True, "temporal": True, "metadata": True, "noise": True, "chroma": True, "flip": True},
    }
    return plans.get(level, plans["basic"])


@dataclass
class Candidate:
    start: float
    end: float
    text: str
    local_score: float
    external_score: float
    platform_fit: float
    combined: float
    index: int = 0


class Pipeline:
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        on_progress: Optional[Callable[[str, float], None]] = None,
    ):
        self.audio_proc = AudioProcessor()
        self.transcriber = WhisperTranscriber(model_size=model_size, use_faster=True)
        self.device = device
        self.hook_engine = ViralHookEngine()
        self.on_progress = on_progress or (lambda msg, pct: print(f"[{pct:.0f}%] {msg}"))
        self._hook_regex = re.compile(
            r"\b(agora|segredo|erro|nunca|sempre|como|por que|porque|atenção|urgente|resultado)\b",
            re.IGNORECASE,
        )

    def _platform_duration_target(self, platform: str) -> float:
        return {
            "tiktok": 28.0,
            "reels": 35.0,
            "shorts": 32.0,
        }.get(platform, 30.0)

    def _normalize_segments(self, raw_segments: List[dict]) -> List[Dict]:
        normalized = []
        for item in raw_segments or []:
            if not isinstance(item, dict):
                continue
            start = float(item.get("start", 0.0) or 0.0)
            end = float(item.get("end", start) or start)
            text = str(item.get("text", "")).strip()
            if end > start and text:
                normalized.append({"start": start, "end": end, "text": text})
        return normalized

    def _segment_from_transcript(
        self,
        transcript_segments: List[Dict],
        min_sec: float = 18.0,
        max_sec: float = 45.0,
    ) -> List[Tuple[float, float, str]]:
        """
        Junta segmentos de transcrição em janelas úteis para corte.
        """
        if not transcript_segments:
            return []

        windows: List[Tuple[float, float, str]] = []
        i = 0
        n = len(transcript_segments)
        while i < n:
            start = transcript_segments[i]["start"]
            text_parts = []
            j = i
            end = start
            while j < n:
                end = transcript_segments[j]["end"]
                text_parts.append(transcript_segments[j]["text"])
                duration = end - start
                if duration >= min_sec:
                    # fecha no primeiro ponto bom entre min e max
                    if duration <= max_sec:
                        break
                    # excedeu max: fecha no anterior se possível
                    if j > i:
                        prev = transcript_segments[j - 1]
                        end = prev["end"]
                        text_parts.pop()
                    break
                j += 1

            if end - start >= min_sec:
                windows.append((start, end, " ".join(text_parts).strip()))
            i = max(j + 1, i + 1)
        return windows

    def _candidate_score(self, text: str, start: float, end: float, platform: str) -> Candidate:
        duration = max(end - start, 0.1)
        hook_hits = len(self._hook_regex.findall(text))
        hook_density = min(hook_hits / max(len(text.split()), 1), 0.25)

        # Motor de hooks (viral_engine)
        archetype = "revelacao" if hook_hits > 0 else "despertar"
        generated_hooks = self.hook_engine.generate(archetype, text)
        hook_bonus = min(sum(len(v) for v in generated_hooks.values()) / 1200.0, 0.12)

        # Sinal de retenção (textos mais "densos" e curtos tendem a performar melhor)
        word_count = max(len(text.split()), 1)
        words_per_sec = word_count / duration
        retention = max(0.0, min(1.0, (words_per_sec / 2.8)))

        # Fit por duração + energia (viral_engine/platform_optimizer)
        energy = min(words_per_sec / 3.0, 1.0)
        fit_raw = platform_fit_score("geral", duration, energy)
        platform_fit = max(0.0, min(1.0, fit_raw.get(platform, 0.0) / 100.0))

        local_score = max(0.0, min(1.0, 0.50 + hook_density + hook_bonus + 0.25 * retention))
        external_score = max(0.0, min(1.0, 0.45 + 0.35 * retention))
        combined_base = evaluate_decision(
            local_score=local_score,
            external_score=external_score,
            platform_fit=platform_fit,
            transcription_quality=0.9 if text else 0.45,
        )
        duration_fit = platform_fit
        transcription_quality = 0.9 if text else 0.45
        combined = (
            0.50 * local_score
            + 0.30 * external_score
            + 0.10 * platform_fit
            + 0.05 * duration_fit
            + 0.05 * transcription_quality
        )
        # mantém compatibilidade com engine antiga
        combined = max(combined, combined_base * 0.95)
        return Candidate(
            start=start,
            end=end,
            text=text,
            local_score=local_score,
            external_score=external_score,
            platform_fit=platform_fit,
            combined=combined,
        )

    def run(
        self,
        video_path: str,
        platform: str = "tiktok",
        protection: str = "basic",
        max_cuts: int = 5,
        output_dir: Optional[str] = None,
        export_prompt_path: Optional[str] = None,
        prompt_only: bool = False,
        ai_response_path: Optional[str] = None,
    ) -> List[str]:
        video_path = str(Path(video_path).resolve())
        base_name = Path(video_path).stem
        out_dir = Path(output_dir or f"./clipfusion_output_{base_name}")
        out_dir.mkdir(parents=True, exist_ok=True)

        self.on_progress("Criando projeto...", 5)
        project_id = create_project(base_name, video_path, language="pt")

        self.on_progress("Extraindo e limpando áudio...", 15)
        audio_path = self.audio_proc.extract_and_clean(video_path)

        self.on_progress("Transcrevendo...", 35)
        result = self.transcriber.transcribe(audio_path, language="pt")
        text = result.get("text", "")
        raw_segments = self._normalize_segments(result.get("segments", []))

        save_transcription(
            project_id=project_id,
            full_text=text,
            segments_json=json.dumps(raw_segments, ensure_ascii=False),
            quality_score=0.85 if text else 0.0,
        )

        self.on_progress("Segmentando e criando candidatos...", 55)
        transcript_windows = self._segment_from_transcript(raw_segments, min_sec=18.0, max_sec=45.0)

        pause_windows = []
        for start, end in segment_by_pauses(video_path, min_sec=18, max_sec=45):
            snippet = text[:800] if text else ""
            pause_windows.append((float(start), float(end), snippet))

        candidate_windows = transcript_windows or pause_windows
        if not candidate_windows:
            duration = self.audio_proc.get_duration(video_path)
            if duration > 0:
                candidate_windows = [(0.0, min(35.0, duration), text[:800] if text else "")]

        scored: List[Candidate] = []
        for idx, (start, end, snippet) in enumerate(candidate_windows[: max_cuts * 3], 1):
            cand = self._candidate_score(snippet or text[:800], start, end, platform=platform)
            cand.index = idx
            scored.append(cand)

        # Exporta prompt para IA externa manual (sem API)
        if export_prompt_path:
            prompt_payload = [
                {
                    "index": c.index,
                    "start": c.start,
                    "end": c.end,
                    "duration": round(c.end - c.start, 2),
                    "text": c.text,
                    "local_combined": round(c.combined, 4),
                }
                for c in scored
            ]
            prompt_text = build_external_ai_prompt(text, prompt_payload, platform=platform)
            Path(export_prompt_path).parent.mkdir(parents=True, exist_ok=True)
            Path(export_prompt_path).write_text(prompt_text, encoding="utf-8")
            self.on_progress(f"Prompt para IA externa salvo em: {export_prompt_path}", 66)
            if prompt_only:
                self.on_progress("Prompt-only: pipeline encerrado antes do render.", 100)
                return []

        # Re-rankeia com resposta externa (se fornecida)
        if ai_response_path and Path(ai_response_path).exists():
            raw_external = Path(ai_response_path).read_text(encoding="utf-8")
            normalized_external = normalize_external_ai_response(parse_ai_response(raw_external))
            for c in scored:
                ext = normalized_external.get(c.index)
                if not ext:
                    continue
                ext_score = max(0.0, min(1.0, ext.get("external_score", c.external_score)))
                hook = max(0.0, min(1.0, ext.get("hook_strength", c.local_score)))
                retention = max(0.0, min(1.0, ext.get("retention_score", c.external_score)))
                duration_fit = max(0.0, min(1.0, ext.get("duration_fit", c.platform_fit)))
                transcription_quality = max(0.0, min(1.0, ext.get("transcription_quality", 0.9 if c.text else 0.45)))
                c.local_score = (c.local_score * 0.5) + (hook * 0.5)
                c.external_score = (c.external_score * 0.4) + (retention * 0.6)
                c.combined = (
                    0.50 * c.local_score
                    + 0.30 * ext_score
                    + 0.10 * c.platform_fit
                    + 0.05 * duration_fit
                    + 0.05 * transcription_quality
                )
            self.on_progress(f"Resposta externa aplicada: {ai_response_path}", 70)

        scored.sort(key=lambda x: x.combined, reverse=True)
        top_candidates = scored[:max_cuts]
        plan = build_plan(protection)
        outputs = []

        for idx, cand in enumerate(top_candidates, 1):
            progress = 75 + (idx / max(len(top_candidates), 1)) * 25.0
            self.on_progress(f"Renderizando corte {idx}/{len(top_candidates)}...", progress)

            start, end = cand.start, cand.end
            seg = (start, end)
            out_path = str(out_dir / f"{base_name}_cut_{idx:02d}_{platform}.mp4")

            candidate_id = save_candidate(
                project_id=project_id,
                transcript_id=project_id,
                start=start,
                end=end,
                text=cand.text[:5000] if cand.text else text[:5000],
                scores={
                    "hook_strength": cand.local_score,
                    "retention_score": cand.external_score,
                    "moment_strength": cand.combined,
                    "shareability": (cand.local_score + cand.external_score) / 2.0,
                    "platform_fit_tiktok": cand.platform_fit if platform == "tiktok" else 0.0,
                    "platform_fit_reels": cand.platform_fit if platform == "reels" else 0.0,
                    "platform_fit_shorts": cand.platform_fit if platform == "shorts" else 0.0,
                    "combined_score": cand.combined,
                },
            )

            cut_id = save_cut(project_id, candidate_id, out_path)
            update_cut_status(cut_id, "rendering")
            try:
                render_cut(video_path, seg, plan, platform, out_path)
                update_cut_status(cut_id, "done")
                update_cut_output(cut_id, out_path)
                outputs.append(out_path)
            except Exception as exc:
                update_cut_status(cut_id, f"error: {exc}")
                raise

        self.on_progress("Concluído!", 100)
        return outputs
