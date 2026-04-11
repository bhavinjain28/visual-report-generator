"""
Builds a downloadable PDF report combining analysis data + Gemini-generated visuals.
Uses ReportLab for PDF generation.
"""
import io
import json
from datetime import datetime


def build_pdf(report: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        # Fallback: minimal PDF using basic bytes
        return _minimal_pdf(report)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    navy = colors.HexColor('#0f172a')
    teal = colors.HexColor('#06b6d4')
    purple = colors.HexColor('#8b5cf6')
    light_gray = colors.HexColor('#f1f5f9')
    red = colors.HexColor('#ef4444')
    green = colors.HexColor('#22c55e')

    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  textColor=navy, fontSize=22, spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     textColor=teal, fontSize=12, spaceAfter=16)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
                                    textColor=purple, fontSize=14, spaceBefore=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                 textColor=navy, fontSize=10, leading=14)
    small_style = ParagraphStyle('Small', parent=styles['Normal'],
                                  textColor=colors.gray, fontSize=8)

    story = []

    # Header
    title = report.get('title') or report.get('filename', 'Document Report')
    doc_type = report.get('document_type', 'Document')
    created_at = report.get('created_at', datetime.now().isoformat())[:10]

    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"{doc_type} · Analyzed {created_at} · Powered by Claude AI + Gemini", subtitle_style))
    story.append(HRFlowable(width='100%', color=teal, thickness=2))
    story.append(Spacer(1, 12))

    # Summary
    summary = report.get('summary', '')
    if summary:
        story.append(Paragraph('Summary', heading_style))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 8))

    # Key Metrics
    metrics = report.get('key_metrics', [])
    if metrics:
        story.append(Paragraph('Key Metrics', heading_style))
        data = [['Metric', 'Value', 'Trend']]
        for m in metrics[:8]:
            trend = {'up': '↑', 'down': '↓', 'neutral': '—'}.get(str(m.get('trend', '')).lower(), '—')
            val = f"{m.get('value', '')} {m.get('unit', '') or ''}".strip()
            data.append([m.get('label', ''), val, trend])
        t = Table(data, colWidths=[8*cm, 5*cm, 2*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), light_gray),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Key Fields
    key_fields = report.get('key_fields', {})
    if key_fields and isinstance(key_fields, dict) and len(key_fields) > 0:
        story.append(Paragraph('Key Fields', heading_style))
        data = [['Field', 'Value']]
        for k, v in list(key_fields.items())[:10]:
            data.append([str(k), str(v)[:80]])
        t = Table(data, colWidths=[6*cm, 9*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), purple),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Insights
    insights = report.get('insights', [])
    if insights:
        story.append(Paragraph('Insights', heading_style))
        for ins in insights[:6]:
            story.append(Paragraph(f'• {ins}', body_style))
        story.append(Spacer(1, 8))

    # Risk Flags
    risk_flags = report.get('risk_flags', [])
    if risk_flags:
        story.append(Paragraph('Risk Flags', heading_style))
        risk_style = ParagraphStyle('Risk', parent=body_style, textColor=red)
        for rf in risk_flags:
            story.append(Paragraph(f'⚠ {rf}', risk_style))
        story.append(Spacer(1, 8))

    # Metadata footer
    story.append(HRFlowable(width='100%', color=colors.HexColor('#e2e8f0'), thickness=1))
    story.append(Spacer(1, 6))
    sentiment = report.get('sentiment', 'Neutral')
    confidence = report.get('confidence', 0.5)
    story.append(Paragraph(
        f'Sentiment: {sentiment}  ·  Confidence: {int(confidence * 100)}%  ·  '
        f'Report ID: {report.get("id", "N/A")}  ·  Generated by Visual Report Builder',
        small_style
    ))

    doc.build(story)
    return buffer.getvalue()


def _minimal_pdf(report):
    """Very basic fallback PDF if reportlab not installed."""
    content = f"%PDF-1.4\n% Report: {report.get('title', 'Document')}\n"
    return content.encode('latin-1')
