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

    # ── Retail KPIs ───────────────────────────────────────────────────────────
    retail_kpis = report.get('retail_kpis', {})
    if retail_kpis:
        story.append(HRFlowable(width='100%', color=colors.HexColor('#22c55e'), thickness=1))
        story.append(Paragraph('Retail Intelligence', heading_style))

        kpi_rows = [['KPI', 'Value']]
        total_rev = retail_kpis.get('total_revenue')
        if total_rev is not None:
            rev_display = f"Rs {total_rev/1e7:.2f} Cr" if total_rev >= 1e7 else \
                          f"Rs {total_rev/1e5:.2f} L" if total_rev >= 1e5 else \
                          f"Rs {total_rev:,.0f}"
            kpi_rows.append(['Total Revenue', rev_display])
        if retail_kpis.get('avg_transaction') is not None:
            kpi_rows.append(['Avg Transaction', f"Rs {retail_kpis['avg_transaction']:,.2f}"])
        if retail_kpis.get('num_transactions') is not None:
            kpi_rows.append(['Transactions', f"{retail_kpis['num_transactions']:,}"])
        if retail_kpis.get('top_category'):
            pct = retail_kpis.get('top_category_pct', 0)
            kpi_rows.append(['Top Category', f"{retail_kpis['top_category']} ({pct:.1f}% of revenue)"])
        if retail_kpis.get('total_skus') is not None:
            kpi_rows.append(['Total SKUs', str(retail_kpis['total_skus'])])
        if retail_kpis.get('total_units') is not None:
            kpi_rows.append(['Units Sold', f"{retail_kpis['total_units']:,.0f}"])
        if retail_kpis.get('latest_mom_pct') is not None:
            mom = retail_kpis['latest_mom_pct']
            arrow = '▲' if mom >= 0 else '▼'
            kpi_rows.append(['Latest MoM Growth', f"{arrow} {abs(mom):.1f}%"])

        t = Table(kpi_rows, colWidths=[7*cm, 8*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbf7d0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

        # Top Products
        top_products = retail_kpis.get('top_products', {})
        if top_products:
            story.append(Paragraph('Top 5 Products by Revenue', heading_style))
            prod_rows = [['Product', 'Revenue']]
            for name, rev in top_products.items():
                rev_fmt = f"Rs {rev/1e5:.2f} L" if rev >= 1e5 else f"Rs {rev:,.0f}"
                prod_rows.append([str(name)[:40], rev_fmt])
            t2 = Table(prod_rows, colWidths=[10*cm, 5*cm])
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbf7d0')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t2)
            story.append(Spacer(1, 8))

        # MoM Growth
        mom_growth = retail_kpis.get('mom_growth', {})
        if mom_growth:
            story.append(Paragraph('Month-over-Month Revenue Growth', heading_style))
            mom_rows = [['Month', 'Growth %']]
            for month, pct in mom_growth.items():
                arrow = '▲' if pct >= 0 else '▼'
                mom_rows.append([str(month), f"{arrow} {abs(pct):.1f}%"])
            t3 = Table(mom_rows, colWidths=[8*cm, 7*cm])
            t3.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#166534')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbf7d0')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t3)
            story.append(Spacer(1, 8))

    # ── Anomaly Radar ─────────────────────────────────────────────────────────
    retail_anomalies = report.get('retail_anomalies', [])
    if retail_anomalies:
        story.append(Paragraph('Anomaly Radar', heading_style))
        orange = colors.HexColor('#ea580c')
        a_rows = [['Item', 'Column', 'Value', 'Expected Range', 'Direction']]
        for a in retail_anomalies[:12]:
            lo, hi = a.get('expected_range', [0, 0])
            a_rows.append([
                str(a.get('label', ''))[:28],
                str(a.get('column', '')),
                f"{a.get('value', 0):,.2f}",
                f"[{lo:,.2f} – {hi:,.2f}]",
                ('HIGH ↑' if a.get('direction') == 'high' else 'LOW ↓'),
            ])
        t = Table(a_rows, colWidths=[4*cm, 3*cm, 2.5*cm, 4*cm, 2*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c2d12')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff7ed')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fed7aa')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # ── Root Cause Analysis ───────────────────────────────────────────────────
    retail_rca = report.get('retail_rca', {})
    if retail_rca:
        story.append(Paragraph('AI Root Cause Analysis', heading_style))

        if retail_rca.get('root_cause_summary'):
            rca_style = ParagraphStyle('RCA', parent=body_style,
                                       textColor=colors.HexColor('#4338ca'),
                                       borderPadding=8)
            story.append(Paragraph(retail_rca['root_cause_summary'], rca_style))
            story.append(Spacer(1, 6))

        driver_tree = retail_rca.get('driver_tree', [])
        if driver_tree:
            story.append(Paragraph('Causal Driver Tree', heading_style))
            d_rows = [['Driver', 'Impact', 'Evidence']]
            for d in driver_tree:
                d_rows.append([
                    str(d.get('driver', ''))[:30],
                    str(d.get('impact', '')).upper(),
                    str(d.get('evidence', ''))[:60],
                ])
                for sd in d.get('sub_drivers', []):
                    d_rows.append([
                        f"  ↳ {str(sd.get('driver', ''))[:26]}",
                        str(sd.get('impact', '')).upper(),
                        str(sd.get('evidence', ''))[:60],
                    ])
            t = Table(d_rows, colWidths=[4.5*cm, 2*cm, 9*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1b4b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eef2ff')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7d2fe')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        if retail_rca.get('recommended_actions'):
            story.append(Paragraph('Recommended Actions', heading_style))
            act_style = ParagraphStyle('Act', parent=body_style, textColor=colors.HexColor('#166534'))
            for i, action in enumerate(retail_rca['recommended_actions'], 1):
                story.append(Paragraph(f'{i}. {action}', act_style))
            story.append(Spacer(1, 6))

        if retail_rca.get('monitoring_metrics'):
            story.append(Paragraph('Monitor Going Forward', heading_style))
            metrics_text = '  ·  '.join(retail_rca['monitoring_metrics'])
            story.append(Paragraph(metrics_text, body_style))
            story.append(Spacer(1, 6))

        conf_pct = int(retail_rca.get('confidence', 0.5) * 100)
        story.append(Paragraph(f'RCA Confidence: {conf_pct}%', small_style))
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
