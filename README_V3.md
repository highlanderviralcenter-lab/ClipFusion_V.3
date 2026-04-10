# ClipFusion V3 (pacote limpo)

Esta pasta contém **somente os arquivos canônicos criados** na consolidação, sem cópias históricas.

## Estrutura
- `app_V3/` código da aplicação
- `scripts_V3/` instaladores e diagnósticos
- `docs_V3/` documentação consolidada

## Execução rápida
```bash
cd app_V3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_V3.txt
bash run_V3.sh
```

## Observação importante
Os arquivos principais foram renomeados com sufixo `_V3` para diferenciar da V2:
- `main_V3.py`
- `db_V3.py`
- `requirements_V3.txt`
- `run_V3.sh`
- scripts em `scripts_V3/*_V3.sh`
- `manual_tecnico_V3.md`
