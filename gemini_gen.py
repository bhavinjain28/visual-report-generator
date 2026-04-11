import os
import base64
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

STATIC_DIR = Path(__file__).parent / 'static' / 'reports'
STATIC_DIR.mkdir(parents=True, exist_ok=True)

HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"


def generate_visuals(report: dict) -> list:
    """Generate 3 infographic panels using Hugging Face FLUX (free tier)."""
    api_key = os.environ.get('HF_API_KEY')
    if not api_key:
        raise ValueError("HF_API_KEY not set in .env — get your free token at huggingface.co/settings/tokens")

    analysis = report.get('analysis', report)
    prompts = _build_prompts(analysis, report.get('id', 0))
    images = []

    for i, prompt in enumerate(prompts):
        if i > 0:
            time.sleep(3)
        try:
            img_bytes = _call_hf(prompt, api_key)
            b64 = base64.b64encode(img_bytes).decode('utf-8')

            img_path = STATIC_DIR / f"report_{report.get('id', 0)}_panel_{i+1}.png"
            with open(img_path, 'wb') as f:
                f.write(img_bytes)

            images.append({
                'panel': i + 1,
                'b64': b64,
                'path': f'/static/reports/report_{report.get("id", 0)}_panel_{i+1}.png'
            })

        except Exception as e:
            images.append({
                'panel': i + 1,
                'b64': None,
                'error': str(e),
                'path': None
            })

    return images


def _call_hf(prompt: str, api_key: str, retries: int = 3) -> bytes:
    """Call HuggingFace Inference API, retry if model is loading."""
    payload = json.dumps({
        "inputs": prompt,
        "parameters": {"num_inference_steps": 4, "guidance_scale": 0.0}
    }).encode('utf-8')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    for attempt in range(retries):
        req = urllib.request.Request(HF_API_URL, data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                # If response is JSON it's an error, if bytes it's the image
                try:
                    err = json.loads(data)
                    if 'estimated_time' in err:
                        wait = min(err['estimated_time'], 30)
                        time.sleep(wait)
                        continue
                    raise Exception(err.get('error', str(err)))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return data  # Raw image bytes
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            try:
                err_json = json.loads(body)
                if 'estimated_time' in err_json:
                    time.sleep(min(err_json['estimated_time'], 30))
                    continue
                raise Exception(err_json.get('error', body))
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {body[:200]}")

    raise Exception("Model still loading after retries — try again in 30 seconds")


def _build_prompts(analysis: dict, report_id: int) -> list:
    title = analysis.get('title', 'Document Report')
    doc_type = analysis.get('document_type', 'Document')
    summary = analysis.get('summary', '')
    metrics = analysis.get('key_metrics', [])
    insights = analysis.get('insights', [])
    risk_flags = analysis.get('risk_flags', [])
    sentiment = analysis.get('sentiment', 'Neutral')
    confidence = analysis.get('confidence', 0.5)
    infographic_prompt = analysis.get('infographic_prompt', '')

    metrics_text = ', '.join(
        f"{m['label']}: {m['value']}{' ' + m['unit'] if m.get('unit') else ''}"
        for m in metrics[:5]
    ) if metrics else 'no specific metrics'

    insights_list = ' | '.join(insights[:3]) if insights else 'Analysis complete'
    risks_text = ', '.join(risk_flags[:2]) if risk_flags else 'none'

    panel1 = infographic_prompt if infographic_prompt else (
        f"Professional business intelligence dashboard infographic. Dark navy background. "
        f"Teal and purple glowing accents. Title: '{title}'. Document type: '{doc_type}'. "
        f"Summary: '{summary[:150]}'. Key metrics: {metrics_text}. Sentiment: {sentiment}. "
        f"Modern flat UI design, clean sans-serif typography, geometric shapes. No people."
    )

    panel2 = (
        f"Professional insights report card. Dark background, gold accents. "
        f"Header: 'Key Insights' for '{title}'. "
        f"Bullet points: {insights_list}. "
        f"Risk flags section: {len(risk_flags)} flags — {risks_text}. "
        f"Clean minimal flat design, white text, checkmark icons. No people."
    )

    panel3 = (
        f"Analytics scorecard infographic. Dark blue to purple gradient background. "
        f"Title: 'Analysis Report', subtitle: '{doc_type}'. "
        f"4 stat cards: Confidence {int(confidence*100)}%, "
        f"Metrics {len(metrics)}, Insights {len(insights)}, Risk Flags {len(risk_flags)}. "
        f"Teal progress bar at {int(confidence*100)}%. Badge: 'Powered by Claude AI'. "
        f"Minimal modern UI, bold numbers, glowing cards. No people."
    )

    return [panel1, panel2, panel3]
