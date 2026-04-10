# SignalCut Hybrid (ClipFusion V2) — Manual Técnico Consolidado

## Arquitetura
Fluxo híbrido: **Local → IA Externa → Local**.

## Pipeline
1. Ingestão/transcrição local (faster-whisper).
2. Segmentação por pausas (18-35s).
3. Scoring local + prompt estruturado.
4. Refino por IA externa (JSON).
5. Render 2-pass com proteção anti-copyright.

## Regra de Ouro
`final = local*0.50 + external*0.30 + platform_fit*0.10 + duration_fit*0.05 + transcription_quality*0.05`

## Hardware alvo
- i5-6200U + Intel HD 520
- 8GB RAM + zRAM 6GB (LZ4) + swap 2GB
- `i915.enable_guc=3`

## Operação
- `scripts/install_debian.sh`
- `app/run.sh`
- `scripts/render_2pass.sh`
