import os
import json
import re
import anthropic
from dotenv import load_dotenv
load_dotenv()

def _get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)

SYSTEM_PROMPT = """You are a document intelligence and data analyst AI.
Analyze the provided document and return ONLY valid JSON (no markdown, no code fences) matching this schema exactly:

{
  "document_type": "string (e.g. Invoice, Contract, Report, Receipt, Resume, Research Paper, Financial Statement, CSV Data, Other)",
  "title": "string — inferred document title or topic",
  "summary": "string — 2-3 sentence plain-English summary",
  "key_metrics": [
    {"label": "string", "value": "string", "unit": "string or null", "trend": "up|down|neutral|null"}
  ],
  "key_fields": {"field_name": "value"},
  "insights": ["string — actionable insight or notable finding"],
  "risk_flags": ["string — risks, anomalies, or concerns found"],
  "sentiment": "Positive|Neutral|Negative",
  "confidence": 0.0,
  "chart_data": {
    "bar": {"labels": [], "values": [], "title": "string or null"},
    "pie": {"labels": [], "values": [], "title": "string or null"},
    "line": {"labels": [], "values": [], "title": "string or null"}
  },
  "infographic_prompt": "string — a detailed prompt for an AI image generator to create a professional infographic summarizing this document. Describe layout, colors, icons, and key stats to show."
}

Rules:
- key_metrics: extract up to 8 real numbers/stats from the document
- chart_data: populate whichever charts make sense (leave empty arrays [] if not applicable)
- infographic_prompt: be very specific — mention colors (use blues/teals/purples), mention layout (e.g. '3-column layout'), mention specific numbers from the document
- confidence: 0.0-1.0 float representing how confident you are in the extraction
- Return ONLY the JSON object, nothing else."""


def analyze(extracted: dict, filename: str) -> dict:
    client = _get_client()
    content = []

    if extracted.get('image_b64') and extracted.get('mime_type'):
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": extracted['mime_type'],
                    "data": extracted['image_b64']
                }
            },
            {"type": "text", "text": f"Analyze this document (filename: {filename}). Return ONLY JSON."}
        ]
    else:
        text = extracted.get('text', '')[:15000]
        content = [{"type": "text", "text": f"Filename: {filename}\n\nDocument content:\n{text}\n\nReturn ONLY JSON."}]

    try:
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        return _normalize(data)
    except json.JSONDecodeError as e:
        return {'error': f'JSON parse error: {e}', 'raw': raw[:500]}
    except Exception as e:
        return {'error': str(e)}


def _normalize(data: dict) -> dict:
    defaults = {
        'document_type': 'Unknown',
        'title': 'Untitled Document',
        'summary': '',
        'key_metrics': [],
        'key_fields': {},
        'insights': [],
        'risk_flags': [],
        'sentiment': 'Neutral',
        'confidence': 0.5,
        'chart_data': {'bar': {'labels': [], 'values': [], 'title': None},
                       'pie': {'labels': [], 'values': [], 'title': None},
                       'line': {'labels': [], 'values': [], 'title': None}},
        'infographic_prompt': ''
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return data
