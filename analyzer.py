"""
Hybrid AI analysis pipeline
===========================
Pass 1 — Haiku (fast, cheap): classify document type + industry, extract title.
Pass 2 — Sonnet (deep): industry-expert analysis with benchmarks, health score,
         prioritized recommendations, and richer chart data.

Falls back to Haiku for the deep pass if Sonnet is unavailable.
"""

import os
import json
import re
import anthropic
from dotenv import load_dotenv

from industry_knowledge import (
    resolve_industry, get_profile, build_industry_prompt_block, INDUSTRY_PROFILES
)

load_dotenv()

HAIKU_MODEL = os.environ.get('FAST_MODEL', 'claude-haiku-4-5-20251001')
SONNET_MODEL = os.environ.get('DEEP_MODEL', 'claude-sonnet-4-6')


def _get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def _parse_json(raw: str) -> dict:
    """Robust JSON extraction: strips code fences, trims to outermost braces."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    start, end = raw.find('{'), raw.rfind('}')
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last-ditch: drop trailing commas, then try to auto-close
        cleaned = re.sub(r',(\s*[}\]])', r'\1', raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return json.loads(_close_truncated_json(cleaned))


def _close_truncated_json(raw: str) -> str:
    """Salvage JSON cut off mid-structure by closing open braces/brackets/strings."""
    # Walk the string tracking open containers, ignoring chars inside strings.
    stack = []
    in_str = False
    escape = False
    last_good = 0  # index of last char that's safe to truncate at
    for i, ch in enumerate(raw):
        if escape:
            escape = False
            continue
        if ch == '\\' and in_str:
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in '{[':
            stack.append('}' if ch == '{' else ']')
        elif ch in '}]':
            if stack:
                stack.pop()
        if not in_str and ch in '}],':
            last_good = i + 1
    # Truncate to the last safe boundary, drop dangling comma, then close.
    out = raw[:last_good].rstrip().rstrip(',')
    if in_str:
        out += '"'
    out += ''.join(reversed(stack))
    return out


TEXT_BUDGET = 60000  # chars sent to the deep-analysis pass
FRONT_MATTER_CHARS = 8000  # always keep this much from the top (title, TOC, intro)

# Keywords that mark high-signal paragraphs in RFPs/PWSs/contracts.
# Grouped for readability; matched case-insensitively.
_SIGNAL_TERMS = (
    # Modal / requirement language
    'shall', 'must', 'required', 'mandatory', 'contractor shall', 'government shall',
    # Contract mechanics
    'sla', 'service level', 'response time', 'deduction', 'penalty',
    'liquidated damages', 'termination', 'default', 'cure period',
    'option year', 'period of performance', 'transition', 'phase-in',
    # Pricing signals
    'wage', 'davis-bacon', 'sca ', 'prevailing wage', 'per hour', 'per sq ft',
    'square foot', 'square feet', 'price', 'cost', 'fee', 'not to exceed',
    # Compliance / qualification
    'insurance', 'bond', 'certif', 'clearance', 'license', 'past performance',
    'key personnel', 'quality control', 'quality assurance', 'inspection',
    'small business', 'set-aside', 'set aside', 'socioeconomic',
    # Scope / operations
    'scope of work', 'statement of work', 'frequency', 'schedule', 'shift',
    'coverage', 'staffing', 'fte', 'productivity', 'workload',
    'square footage', 'building', 'facility', 'restroom', 'floor',
    # Deadlines / submission
    'due date', 'submission', 'submit', 'deadline', 'questions due',
    'proposal due', 'site visit', 'pre-proposal',
)


def _prepare_text(raw: str, budget: int = TEXT_BUDGET) -> str:
    """
    Trim document text to fit the analysis budget without losing what matters.

    For short docs: return unchanged.
    For large docs (RFPs, PWSs, long contracts): always keep the front matter
    (title, TOC, background — that's where document identity lives), then
    score the remaining paragraphs by requirement-signal keywords and fill
    the remaining budget with the highest-scoring paragraphs in original
    document order. This preserves the sections that actually drive pricing
    decisions instead of blindly truncating at char N.
    """
    raw = raw or ''
    if len(raw) <= budget:
        return raw

    front_budget = min(FRONT_MATTER_CHARS, budget)
    front = raw[:front_budget]
    tail = raw[front_budget:]

    # Split remaining text into paragraphs (blank-line separated).
    paras = [p for p in re.split(r'\n\s*\n', tail) if p.strip()]

    # Score each paragraph by number of signal-term hits (weighted by term length
    # so multi-word phrases count more than single words).
    def score(p: str) -> int:
        lower = p.lower()
        return sum(lower.count(t) * max(1, len(t.split())) for t in _SIGNAL_TERMS)

    scored = [(i, score(p), p) for i, p in enumerate(paras)]
    scored.sort(key=lambda x: (-x[1], x[0]))  # highest score, then earliest

    remaining_budget = budget - len(front) - 200  # reserve a bit for markers
    picked_idx = set()
    running = 0
    for idx, sc, p in scored:
        if sc == 0:
            break  # no more signal-bearing paragraphs worth including
        cost = len(p) + 2
        if running + cost > remaining_budget:
            continue
        picked_idx.add(idx)
        running += cost

    kept = '\n\n'.join(p for i, p in enumerate(paras) if i in picked_idx)
    marker = f"\n\n[... {len(paras) - len(picked_idx)} lower-signal paragraphs omitted; kept requirement-bearing sections ...]\n\n"
    return front + marker + kept


def _build_content(extracted: dict, filename: str, instruction: str, text_budget: int = TEXT_BUDGET) -> list:
    """Assemble message content for text or vision documents."""
    if extracted.get('image_b64') and extracted.get('mime_type'):
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": extracted['mime_type'],
                    "data": extracted['image_b64'],
                },
            },
            {"type": "text", "text": f"Filename: {filename}\n\n{instruction}"},
        ]
    text = _prepare_text(extracted.get('text', ''), budget=text_budget)
    return [{"type": "text", "text": f"Filename: {filename}\n\nDocument content:\n{text}\n\n{instruction}"}]


# ──────────────────────────────────────────────────────────────────────────────
# Pass 1 — fast classification (Haiku)
# ──────────────────────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are a document triage AI. Classify the document and return ONLY valid JSON:

{
  "document_type": "Invoice | Contract | Report | Receipt | Resume | Research Paper | Financial Statement | CSV Data | Pitch Deck | Policy | RFP | SOW | Other",
  "title": "inferred document title or topic",
  "industry": "one of: retail_ecommerce, finance_banking, corporate_financial, healthcare, technology_saas, manufacturing, real_estate, legal_contracts, hr_recruiting, education, logistics_supply_chain, energy_utilities, hospitality_food, marketing_media, insurance, facilities_services, general",
  "industry_confidence": 0.0,
  "language": "primary language of the document"
}

Pick the industry whose domain expertise would add the MOST analytical value. Use "general"
only when no industry clearly fits. Return ONLY the JSON object."""


def classify(extracted: dict, filename: str) -> dict:
    client = _get_client()
    # Classification only needs the top of the document; keep Haiku fast + cheap.
    content = _build_content(extracted, filename, "Classify this document. Return ONLY JSON.", text_budget=6000)
    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=300,
            system=CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        data = _parse_json(resp.content[0].text)
    except Exception:
        data = {}
    industry_key = resolve_industry(data.get('industry', ''))
    return {
        'document_type': data.get('document_type', 'Document'),
        'title': data.get('title', filename),
        'industry': industry_key,
        'industry_confidence': float(data.get('industry_confidence', 0.5) or 0.5),
        'language': data.get('language', 'English'),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Pass 2 — deep industry analysis (Sonnet, Haiku fallback)
# ──────────────────────────────────────────────────────────────────────────────

DEEP_SCHEMA = """Return ONLY valid JSON (no markdown, no code fences) matching this schema exactly:

{
  "document_type": "string",
  "title": "string — inferred document title or topic",
  "executive_takeaway": "string — ONE punchy sentence: the single most important thing a busy executive should know",
  "summary": "string — 3-4 sentence plain-English summary written for a non-expert",
  "health_score": 0,
  "health_label": "string — 2-4 word verdict matching the score (e.g. 'Strong fundamentals', 'Needs attention')",
  "key_metrics": [
    {"label": "string", "value": "string", "unit": "string or null", "trend": "up|down|neutral|null",
     "benchmark_status": "above|at|below|unknown",
     "context": "string — one short clause comparing to the industry benchmark, or null"}
  ],
  "benchmark_comparison": [
    {"dimension": "string — short axis label (max 3 words)", "document_score": 0, "industry_benchmark": 0,
     "comment": "string — one sentence justifying the scores"}
  ],
  "key_fields": {"field_name": "value"},
  "insights": ["string — specific, benchmark-aware finding (reference actual numbers)"],
  "risk_flags": ["string — risk, anomaly, or concern, with severity context"],
  "opportunities": ["string — concrete improvement or growth opportunity grounded in the data"],
  "recommendations": [
    {"action": "string — specific next step", "priority": "high|medium|low", "rationale": "string — why, in one sentence"}
  ],
  "sentiment": "Positive|Neutral|Negative",
  "confidence": 0.0,
  "chart_data": {
    "bar": {"labels": [], "values": [], "title": "string or null"},
    "pie": {"labels": [], "values": [], "title": "string or null"},
    "line": {"labels": [], "values": [], "title": "string or null"}
  },
  "glossary": {"term": "plain-English definition of industry jargon found in the document"},
  "infographic_prompt": "string — detailed prompt for an AI image generator to create a professional infographic of this document"
}

Rules:
- health_score: 0-100 integer judging overall health/quality/favorability of what the document
  describes, judged against industry benchmarks (50 = at benchmark). For neutral documents
  (e.g. a resume, a contract) score how strong/favorable it is for the reader.
- key_metrics: up to 8 REAL numbers from the document. Every metric gets benchmark_status and context.
- benchmark_comparison: exactly 4-6 dimensions, scores 0-100 where industry_benchmark is what a
  typical healthy player scores (~50-70) and document_score is this document's standing. Choose
  dimensions relevant to the industry (e.g. Profitability, Growth, Liquidity, Efficiency, Risk).
- insights: 4-6 items. Each MUST cite a number from the document and, where possible, a benchmark.
- recommendations: 3-5 items, ordered by priority.
- glossary: 3-6 jargon terms actually present in the document; {} if none.
- chart_data: populate whichever charts make sense (empty arrays [] if not applicable). Values must
  be plain numbers (no currency symbols or commas).
- confidence: 0.0-1.0 for extraction confidence.
- Return ONLY the JSON object, nothing else."""


def analyze(extracted: dict, filename: str, classification: dict = None) -> dict:
    """Full hybrid analysis. Returns analysis dict or {'error': ...}."""
    try:
        client = _get_client()
    except Exception as e:
        return {'error': str(e)}

    cls = classification or classify(extracted, filename)
    industry_key = cls['industry']
    industry_block = build_industry_prompt_block(industry_key)

    system_prompt = (
        "You are an elite document intelligence analyst.\n\n"
        f"{industry_block}\n\n"
        f"The document was pre-classified as: {cls['document_type']} (industry: {get_profile(industry_key)['name']}).\n"
        "If the classification looks wrong, correct document_type in your output.\n\n"
        f"{DEEP_SCHEMA}"
    )

    content = _build_content(extracted, filename, "Analyze this document as the industry expert described. Return ONLY JSON.")

    raw = ''
    last_err = {'error': 'Analysis failed'}
    for model in (SONNET_MODEL, HAIKU_MODEL):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            raw = resp.content[0].text
            if getattr(resp, 'stop_reason', None) == 'max_tokens':
                # Truncated mid-JSON — try to salvage by closing open structures
                raw = _close_truncated_json(raw)
            data = _parse_json(raw)
            data = _normalize(data)
            profile = get_profile(industry_key)
            data['industry'] = industry_key
            data['industry_name'] = profile['name']
            data['industry_icon'] = profile['icon']
            data['industry_confidence'] = cls['industry_confidence']
            data['analysis_model'] = model
            if not data.get('document_type'):
                data['document_type'] = cls['document_type']
            if not data.get('title'):
                data['title'] = cls['title']
            return data
        except json.JSONDecodeError as e:
            last_err = {'error': f'JSON parse error: {e}', 'raw': raw[:500]}
        except anthropic.APIError as e:
            last_err = {'error': str(e)}
            continue  # try fallback model
        except Exception as e:
            last_err = {'error': str(e)}
    return last_err


def _normalize(data: dict) -> dict:
    defaults = {
        'document_type': 'Unknown',
        'title': 'Untitled Document',
        'executive_takeaway': '',
        'summary': '',
        'health_score': 50,
        'health_label': '',
        'key_metrics': [],
        'benchmark_comparison': [],
        'key_fields': {},
        'insights': [],
        'risk_flags': [],
        'opportunities': [],
        'recommendations': [],
        'sentiment': 'Neutral',
        'confidence': 0.5,
        'chart_data': {'bar': {'labels': [], 'values': [], 'title': None},
                       'pie': {'labels': [], 'values': [], 'title': None},
                       'line': {'labels': [], 'values': [], 'title': None}},
        'glossary': {},
        'infographic_prompt': '',
    }
    for k, v in defaults.items():
        if k not in data or data[k] is None:
            data[k] = v
    # Clamp health score
    try:
        data['health_score'] = max(0, min(100, int(data['health_score'])))
    except (TypeError, ValueError):
        data['health_score'] = 50
    # Coerce recommendation shape
    recs = []
    for r in data.get('recommendations', []):
        if isinstance(r, str):
            recs.append({'action': r, 'priority': 'medium', 'rationale': ''})
        elif isinstance(r, dict):
            recs.append({
                'action': r.get('action', ''),
                'priority': (r.get('priority') or 'medium').lower(),
                'rationale': r.get('rationale', ''),
            })
    data['recommendations'] = recs
    return data
