from typing import List, Dict

class HybridPromptGenerator:
    def __init__(self, locale='pt'):
        self.locale = locale

    def build_prompt(self, candidates: List[Dict], context: str = ""):
        prompt = f"""Você é um especialista em viralização de conteúdo para plataformas de vídeo curto (TikTok, Reels, Shorts).

## Contexto
{context if context else "Nenhum contexto adicional fornecido."}

## Instruções
Abaixo estão trechos de um vídeo longo, pré-selecionados por um algoritmo como potenciais candidatos a cortes virais.
Para cada trecho, você deve:
1. Avaliar seu potencial viral (nota de 0 a 10).
2. Se a nota for >= 7, forneça:
   - Um título atrativo (máx 60 caracteres)
   - Um gancho (hook) para os primeiros 3 segundos
   - O arquétipo emocional predominante (use um dos 10 arquétipos do ClipFusion: Curiosidade, Medo, Ganância, Urgência, Prova Social, Autoridade, Empatia, Indignação, Exclusividade, Alívio)
   - Uma justificativa breve (por que viralizaria)
   - Plataformas sugeridas (lista com TikTok, Reels, Shorts)
3. Se a nota for < 7, apenas indique que o trecho não é promissor.

## Formato de Resposta (OBRIGATÓRIO - JSON puro)
Responda APENAS com um JSON válido, sem markdown, contendo uma lista de objetos com os campos:
- candidate_id: (opcional, se fornecido)
- start: (float)
- end: (float)
- title: (string)
- hook: (string)
- archetype: (string)
- score: (float)  # nota da IA (0-10)
- platforms: (lista de strings)
- reason: (string)

Exemplo:
[
  {{
    "candidate_id": 1,
    "start": 12.3,
    "end": 35.7,
    "title": "O segredo da prospecção",
    "hook": "Você sabia que 80% dos vendedores erram?",
    "archetype": "Curiosidade",
    "score": 8.5,
    "platforms": ["tiktok", "reels"],
    "reason": "Gancho forte com pergunta retórica, aborda uma dor comum."
  }}
]

## Candidatos
"""
        for cand in candidates:
            prompt += f"\n--- Candidato ID {cand.get('id', '?')} ---\n"
            prompt += f"Timestamp: {cand['start']}s - {cand['end']}s\n"
            prompt += f"Texto: {cand['text']}\n"
            if 'scores' in cand:
                prompt += f"Scores locais: hook={cand['scores'].get('hook', 0):.2f}, retenção={cand['scores'].get('retention', 0):.2f}, momento={cand['scores'].get('moment', 0):.2f}\n"
        prompt += "\nAnalise agora:"
        return prompt
