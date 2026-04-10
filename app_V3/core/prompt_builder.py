"""ClipFusion — Prompt Builder para IA externa."""
import json, re
from viral_engine.archetypes import ARCHETYPES
from core.transcriber import fmt_time


def _detect_lang(text: str) -> str:
    text_l = text.lower()
    pt_markers = (" você ", " não ", " para ", " que ", " com ", " uma ", " de ")
    en_markers = (" you ", " not ", " with ", " the ", " and ", " this ", " that ")
    pt_score = sum(m in text_l for m in pt_markers)
    en_score = sum(m in text_l for m in en_markers)
    if en_score > pt_score:
        return "en"
    return "pt"


def _coverage_sample(segments: list, buckets: int = 10) -> list:
    """
    Seleciona amostras distribuídas por TODA a timeline para reduzir viés de shortlist.
    Não usa ranking local; cobre começo, meio e fim do vídeo.
    """
    if not segments:
        return []
    first = float(segments[0]["start"])
    last = float(segments[-1]["end"])
    span = max(1.0, last - first)
    bucket_size = span / buckets
    sampled = []
    idx = 0
    for b in range(buckets):
        b_start = first + b * bucket_size
        b_end = b_start + bucket_size
        chosen = None
        while idx < len(segments):
            s = segments[idx]
            idx += 1
            if b_start <= float(s["start"]) < b_end:
                chosen = s
                break
        if chosen is not None:
            sampled.append(chosen)
    return sampled


def build_analysis_prompt(segments: list, duration: float, context: str = "") -> str:
    sampled = _coverage_sample(segments, buckets=12)
    joined = " ".join(s.get("text", "") for s in sampled)[:3000]
    lang = _detect_lang(f" {joined} ")
    lines, total = [], 0
    for s in segments:
        line = f"[{fmt_time(s['start'])}] {s['text']}"
        total += len(line) + 1
        if total > 30000:
            lines.append("...(truncado)")
            break
        lines.append(line)
    transcript = "\n".join(lines)
    arch_block = "\n".join(
        f"  {k}: {v['emocao']} — {v['descricao']}"
        for k, v in ARCHETYPES.items())
    ctx = f"\n## CONTEXTO\n{context.strip()}\n" if context.strip() else ""

    lang_block = (
        "Primary language appears to be ENGLISH. Evaluate hooks, emotion and pacing in English first."
        if lang == "en"
        else "Idioma principal detectado: PORTUGUÊS. Avalie gancho, emoção e ritmo em português primeiro."
    )

    coverage = "\n".join(f"[{fmt_time(s['start'])}] {s['text']}" for s in sampled)

    return f"""Você é especialista em engenharia de retenção e viralização de conteúdo curto.
{ctx}
## DURAÇÃO TOTAL: {fmt_time(duration)}
## LANGUAGE / IDIOMA
{lang_block}

## TRANSCRIÇÃO COM TIMESTAMPS
{transcript}

## COBERTURA GLOBAL (amostra distribuída da timeline inteira, sem ranking local)
{coverage}

## ARQUÉTIPOS DISPONÍVEIS
{arch_block}

## PLATAFORMAS
  tiktok: vertical 9:16, ideal 30–60s, máx 180s. Gancho nos primeiros 1–2s.
  reels: vertical 9:16, ideal 15–60s, máx 90s.
  shorts: vertical 9:16, máx 60s.

## TAREFA
Identifique de 3 a 8 cortes com alto potencial viral.
Critérios: gancho forte nos primeiros 3s, valor emocional claro, 20–90s de duração.
Importante: não assuma que os melhores momentos estão no início. Varra mentalmente TODA a timeline.

## RESPOSTA — SOMENTE JSON, SEM MARKDOWN

{{
  "cortes": [
    {{
      "titulo": "título (máx 60 chars)",
      "start": 123.4,
      "end": 187.2,
      "archetype": "05_revelacao",
      "hook": "o que prende nos primeiros 3 segundos",
      "reason": "por que vai viralizar (2 frases)",
      "platforms": ["tiktok", "reels", "shorts"],
      "metadata": {{
        "titulo_post": "título para publicação",
        "descricao": "2–3 frases",
        "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]
      }}
    }}
  ]
}}

Analise agora:"""


def parse_ai_response(text: str) -> list:
    text  = re.sub(r"```json\s*|```\s*", "", text.strip())
    blob = None
    obj_match = re.search(r"\{[\s\S]*\}", text)
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if obj_match:
        blob = obj_match.group()
    elif arr_match:
        blob = arr_match.group()
    if not blob:
        raise ValueError("Nenhum JSON encontrado.")

    parsed = json.loads(blob)
    if isinstance(parsed, list):
        cortes = parsed
    elif isinstance(parsed, dict):
        cortes = parsed.get("cortes", [])
    else:
        cortes = []
    result = []
    for i, c in enumerate(cortes):
        s, e = float(c.get("start", 0) or 0), float(c.get("end", 0) or 0)
        if e > s and (e - s) >= 10:
            result.append({
                "cut_index": i, "title": c.get("titulo", f"Corte {i+1}"),
                "start": s, "end": e,
                "archetype": c.get("archetype", "01_despertar"),
                "hook": c.get("hook", ""), "reason": c.get("reason", ""),
                "platforms": c.get("platforms", ["tiktok", "reels", "shorts"]),
                "metadata": c.get("metadata", {}),
            })
    return result
