import json
import re

def parse_ai_response(response_text: str):
    clean = re.sub(r'```json\s*|\s*```', '', response_text.strip())
    match = re.search(r'\[.*\]', clean, re.DOTALL)
    if not match:
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if not match:
            return None
        try:
            obj = json.loads(match.group())
            return [obj]
        except:
            return None
    try:
        data = json.loads(match.group())
        if isinstance(data, list):
            return data
        else:
            return [data]
    except:
        return None

def validate_ai_cut(cut):
    required = ['start', 'end', 'title', 'hook', 'score']
    for field in required:
        if field not in cut:
            return False
    return True
