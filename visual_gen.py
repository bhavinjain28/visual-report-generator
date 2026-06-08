"""
Generates 3 styled SVG infographic panels using the Claude API.
Replaces the HuggingFace FLUX image generator entirely.
"""
import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()


def _get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def generate_visuals(report: dict) -> list:
    """Generate 3 SVG infographic panels from report data using Claude."""
    client = _get_client()
    analysis = report.get('analysis', report)

    prompts = _build_prompts(analysis)
    panels = []

    for i, (label, prompt) in enumerate(prompts):
        try:
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            svg = _extract_svg(raw)
            panels.append({'panel': i + 1, 'label': label, 'svg': svg, 'error': None})
        except Exception as e:
            panels.append({'panel': i + 1, 'label': label, 'svg': None, 'error': str(e)})

    return panels


def _extract_svg(text: str) -> str:
    """Pull the SVG element out of Claude's response."""
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    if text.strip().startswith('<svg'):
        return text.strip()
    return text.strip()


def _build_prompts(analysis: dict) -> list:
    title = analysis.get('title', 'Document Report')[:50]
    doc_type = analysis.get('document_type', 'Document')
    summary = analysis.get('summary', '')[:200]
    metrics = analysis.get('key_metrics', [])[:6]
    insights = analysis.get('insights', [])[:5]
    risk_flags = analysis.get('risk_flags', [])[:4]
    sentiment = analysis.get('sentiment', 'Neutral')
    confidence = analysis.get('confidence', 0.5)

    sent_color = {'Positive': '#4ade80', 'Negative': '#f87171'}.get(sentiment, '#94a3b8')
    sent_icon = {'Positive': '▲', 'Negative': '▼'}.get(sentiment, '●')

    metrics_text = '\n'.join(
        f"- {m.get('label','')}: {m.get('value','')} {m.get('unit','') or ''}"
        for m in metrics
    ) or '- No metrics extracted'

    insights_text = '\n'.join(f"- {ins[:70]}" for ins in insights) or '- No insights'
    risks_text = '\n'.join(f"- {r[:70]}" for r in risk_flags) or '- None'

    # ── Panel 1: Executive KPI Dashboard ──────────────────────────────────────
    p1 = f"""Create a professional SVG infographic panel (width=800, height=480).

Design spec:
- Background: dark navy #0f172a with a subtle radial gradient glow in the center
- Top bar (height 60px): fill #1e293b, left-aligned title "{title}" in white 20px bold, right-aligned doc type badge "{doc_type}" in teal #06b6d4 with rounded rect background
- Section label "KEY METRICS" in #7c3aed uppercase 10px, letter-spacing 2, at y=85
- Draw up to {len(metrics)} metric cards in a grid (2 columns, rows as needed) starting y=100:
  Each card: rounded rect fill #1e293b, stroke #334155, padding 16px
  Inside: metric label in #94a3b8 11px, metric value in white 22px bold, unit in #64748b 10px
  Use these metrics:
{metrics_text}
- Bottom strip (height 48px) at bottom: fill #0f172a, show sentiment "{sentiment}" with colored dot ({sent_color}), confidence bar "{int(confidence*100)}%" filled teal, "Powered by Claude AI" right-aligned in #475569 10px

Return ONLY the SVG element, nothing else. Make it beautiful and data-rich."""

    # ── Panel 2: Insights & Risk Intelligence ─────────────────────────────────
    p2 = f"""Create a professional SVG infographic panel (width=800, height=480).

Design spec:
- Background: #0f172a
- Top bar (height 56px): fill #1e293b. Left side: "💡 INSIGHTS" in #06b6d4 bold 14px. Right side: "⚠ RISKS" in #ef4444 bold 14px
- Vertical divider line at x=400 from y=56 to y=440, color #1e293b stroke 2px
- Left column (x 20–390): list the following insights as rows, each with a small cyan circle bullet, text in #cbd5e1 12px, line height 32px, starting y=80:
{insights_text}
- Right column (x 420–780): list the following risk flags as rows, each with a small red triangle bullet, text in #fca5a5 12px, line height 32px, starting y=80:
{risks_text}
- Bottom area (y=440–480): fill #0f172a, centered text showing "{len(insights)} insights  ·  {len(risk_flags)} risk flags  ·  Analyzed by Claude AI" in #475569 11px

Return ONLY the SVG element, nothing else. Clean, minimal, professional."""

    # ── Panel 3: Analytics Scorecard ──────────────────────────────────────────
    p3 = f"""Create a professional SVG infographic scorecard panel (width=800, height=480).

Design spec:
- Background: deep navy #0f172a
- Large centered radial gauge chart (cx=200, cy=240, r=130):
  - Background arc (full 270°): stroke #1e293b, strokeWidth 18
  - Filled arc ({int(confidence*100)}% of 270°): stroke #7c3aed, strokeWidth 18, strokeLinecap round
  - Center text: "{int(confidence*100)}%" in white 36px bold, "Confidence" in #94a3b8 12px below
- Right side (x 370–780): 4 large stat boxes in 2x2 grid, each rounded rect #1e293b, inside:
  - Box 1: number "{len(metrics)}" in #06b6d4 32px bold, label "Metrics" in #64748b 11px
  - Box 2: number "{len(insights)}" in #4ade80 32px bold, label "Insights" in #64748b 11px
  - Box 3: number "{len(risk_flags)}" in #f87171 32px bold, label "Risk Flags" in #64748b 11px
  - Box 4: sentiment icon "{sent_icon}" in {sent_color} 32px bold, label "{sentiment}" in #64748b 11px
- Summary text (centered below gauge, y 390–440): "{summary[:120]}" in #94a3b8 11px, max-width 340px, wrapped
- Bottom badge centered: rounded rect #1e1b4b, text "✦ Powered by Claude AI" in #a78bfa 11px bold

Return ONLY the SVG element, nothing else. Bold, modern, data-forward design."""

    return [
        ('KPI Dashboard', p1),
        ('Insights & Risks', p2),
        ('Analytics Scorecard', p3),
    ]
