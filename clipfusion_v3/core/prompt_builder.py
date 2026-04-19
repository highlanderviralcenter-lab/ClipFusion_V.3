"""
Construtor de prompts para o ClipFusion V3.

Combina a detecção de idioma com uma amostragem de cobertura do
transcrito para formar um prompt informativo para a IA externa.
Inclui tratamento robusto da resposta para suportar tanto objetos
quanto arrays JSON.
"""
import json
import re
from typing import Any, Dict, List

def _detect_lang(text: str) -> str:
    """Detecção rudimentar de idioma baseado em caracteres."""
    if re.search(r"[\u0400-\u04FF]", text):
        return "ru"
    if re.search(r"[\u30A0-\u30FF]", text):
        return "ja"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "pt"

def _coverage_sample(text: str, length: int = 200) -> str:
    """Extrai uma amostra representativa do texto."""
    return text[:length] + ("..." if len(text) > length else "")

def lang_block(lang: str) -> str:
    return f"Idioma detectado: {lang.upper()}"

def coverage(text: str) -> str:
    return _coverage_sample(text)

def parse_ai_response(response: str) -> Any:
    """Analisa a resposta da IA tentando decodificar JSON."""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # tenta encontrar o primeiro bloco JSON no texto
        m = re.search(r"\{.*\}", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        # tenta array JSON
        m = re.search(r"\[.*\]", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return response


def build_external_ai_prompt(
    full_text: str,
    candidates: List[Dict[str, Any]],
    platform: str = "tiktok",
) -> str:
    """
    Gera um prompt pronto para colar em IA externa (sem API).
    A IA deve devolver JSON com score/ajustes por candidato.
    """
    lang = _detect_lang(full_text or "")
    sample = _coverage_sample(full_text or "", 1400)
    payload = {
        "task": "rank_video_cuts",
        "platform": platform,
        "golden_formula": "final = local*0.50 + external*0.30 + platform_fit*0.10 + duration_fit*0.05 + transcription_quality*0.05",
        "rules": {
            "duration_target": {"tiktok": "20-35s", "reels": "25-45s", "shorts": "20-40s"}.get(platform, "20-40s"),
            "return_format": {
                "candidates": [
                    {
                        "index": 1,
                        "external_score": 0.0,
                        "hook_strength": 0.0,
                        "retention_score": 0.0,
                        "duration_fit": 0.0,
                        "transcription_quality": 0.0,
                        "reason": "texto curto"
                    }
                ]
            },
        },
        "transcript_sample": sample,
        "candidates": [
            {
                "index": c.get("index"),
                "start": c.get("start"),
                "end": c.get("end"),
                "duration": c.get("duration"),
                "text": c.get("text", "")[:400],
                "local_combined": c.get("local_combined"),
            }
            for c in candidates
        ],
    }
    prompt = [
        "Você é um editor especialista em cortes virais.",
        f"Plataforma alvo: {platform}.",
        lang_block(lang),
        "",
        "Use a fórmula de score informada.",
        "Analise os candidatos abaixo e devolva SOMENTE JSON válido.",
        "Sem markdown, sem comentários extras.",
        "",
        json.dumps(payload, ensure_ascii=False, indent=2),
    ]
    return "\n".join(prompt)


def normalize_external_ai_response(raw: Any) -> Dict[int, Dict[str, float]]:
    """
    Normaliza diferentes formatos de resposta da IA para:
    { index -> {external_score, hook_strength, retention_score} }.
    """
    if isinstance(raw, str):
        raw = parse_ai_response(raw)

    if isinstance(raw, dict) and "candidates" in raw:
        items = raw.get("candidates", [])
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    normalized: Dict[int, Dict[str, float]] = {}

    def _to_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        try:
            return float(value)
        except Exception:
            return default

    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except Exception:
            continue
        normalized[idx] = {
            "external_score": _to_float(item.get("external_score", item.get("score", 0.0)), 0.0),
            "hook_strength": _to_float(item.get("hook_strength", 0.0), 0.0),
            "retention_score": _to_float(item.get("retention_score", 0.0), 0.0),
            "duration_fit": _to_float(item.get("duration_fit", 0.0), 0.0),
            "transcription_quality": _to_float(item.get("transcription_quality", 0.0), 0.0),
        }
    return normalized
