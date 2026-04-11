import streamlit as st
import tempfile
import os
import base64
import json

# Load secrets from Streamlit Cloud secrets manager if available,
# otherwise fall back to .env file for local development
try:
    for key in ["ANTHROPIC_API_KEY", "HF_API_KEY"]:
        if key in st.secrets and not os.environ.get(key):
            os.environ[key] = st.secrets[key]
except Exception as _secrets_err:
    pass  # Running locally without secrets — .env will be used


from processor import extract
from analyzer import analyze
from gemini_gen import generate_visuals
from database import init_db, save_report, get_all_reports, get_report
from report_builder import build_pdf

st.set_page_config(page_title="AI Visual Report Generator", layout="wide", page_icon="📊")

init_db()

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .metric-card {
    background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
    border: 1px solid #3a3a5c;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    margin-bottom: 10px;
  }
  .metric-label { color: #a0a0c0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
  .metric-value { color: #e0e0ff; font-size: 26px; font-weight: 700; }
  .metric-unit  { color: #7070a0; font-size: 12px; margin-top: 2px; }
  .trend-up   { color: #4ade80; font-size: 14px; }
  .trend-down { color: #f87171; font-size: 14px; }

  .summary-box {
    background: #12122a;
    border-left: 4px solid #7c3aed;
    border-radius: 8px;
    padding: 16px 20px;
    color: #c0c0e0;
    font-size: 15px;
    line-height: 1.7;
    margin-bottom: 20px;
  }

  .insight-item {
    background: #0f2027;
    border-left: 3px solid #06b6d4;
    border-radius: 6px;
    padding: 10px 14px;
    color: #b0d8e8;
    margin-bottom: 8px;
    font-size: 14px;
  }
  .risk-item {
    background: #2a0a0a;
    border-left: 3px solid #ef4444;
    border-radius: 6px;
    padding: 10px 14px;
    color: #f8a0a0;
    margin-bottom: 8px;
    font-size: 14px;
  }

  .badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 6px;
  }
  .badge-positive { background: #14532d; color: #4ade80; }
  .badge-neutral  { background: #1e293b; color: #94a3b8; }
  .badge-negative { background: #450a0a; color: #f87171; }
  .badge-type     { background: #1e1b4b; color: #a5b4fc; }
  .badge-conf     { background: #1c1917; color: #d6d3d1; }

  .section-header {
    font-size: 16px;
    font-weight: 700;
    color: #c4b5fd;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #3a3a5c;
  }
  .field-table { width: 100%; border-collapse: collapse; }
  .field-table td { padding: 7px 12px; border-bottom: 1px solid #2a2a4a; font-size: 13px; color: #c0c0e0; }
  .field-table td:first-child { color: #7070a0; width: 40%; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 📊 AI Visual Report Generator")
st.markdown("Upload any document — PDF, text, CSV, or image — to get an instant structured analysis with charts and insights.")

st.divider()

uploaded_file = st.file_uploader("Upload a file", type=["pdf", "txt", "csv", "jpg", "png"])

if uploaded_file:
    ext = uploaded_file.name.split('.')[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    with st.spinner("🔍 Extracting content..."):
        extracted = extract(tmp_path)

    if extracted.get('error'):
        st.error(f"Extraction failed: {extracted['error']}")
    else:
        with st.spinner("🧠 Analyzing with AI..."):
            analysis = analyze(extracted, uploaded_file.name)

        if 'error' in analysis:
            st.error(f"Analysis failed: {analysis['error']}")
            if 'raw' in analysis:
                with st.expander("Raw AI response"):
                    st.code(analysis['raw'])
        else:
            report_id = save_report(
                filename=uploaded_file.name,
                file_type=ext,
                file_size=os.path.getsize(tmp_path),
                analysis=analysis,
                extraction_method=extracted.get('method', 'unknown')
            )

            # ── Title + Badges ──────────────────────────────────────────────────
            sentiment = analysis.get('sentiment', 'Neutral')
            conf = analysis.get('confidence', 0)
            doc_type = analysis.get('document_type', 'Document')

            badge_class = {
                'Positive': 'badge-positive',
                'Negative': 'badge-negative',
            }.get(sentiment, 'badge-neutral')

            sent_icon = {'Positive': '▲', 'Negative': '▼'}.get(sentiment, '●')

            st.markdown(f"### {analysis.get('title', uploaded_file.name)}")
            st.markdown(
                f'<span class="badge badge-type">📄 {doc_type}</span>'
                f'<span class="badge {badge_class}">{sent_icon} {sentiment}</span>'
                f'<span class="badge badge-conf">Confidence: {int(conf*100)}%</span>',
                unsafe_allow_html=True
            )
            st.markdown("")

            # ── Summary ─────────────────────────────────────────────────────────
            if analysis.get('summary'):
                st.markdown('<div class="section-header">📝 Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="summary-box">{analysis["summary"]}</div>', unsafe_allow_html=True)

            # ── KPI Metric Cards ─────────────────────────────────────────────────
            metrics = analysis.get('key_metrics', [])
            if metrics:
                st.markdown('<div class="section-header">📌 Key Metrics</div>', unsafe_allow_html=True)
                cols = st.columns(min(len(metrics), 4))
                for i, m in enumerate(metrics[:8]):
                    trend_html = ''
                    if m.get('trend') == 'up':
                        trend_html = '<div class="trend-up">▲ Up</div>'
                    elif m.get('trend') == 'down':
                        trend_html = '<div class="trend-down">▼ Down</div>'

                    unit_html = f'<div class="metric-unit">{m["unit"]}</div>' if m.get('unit') else ''
                    with cols[i % 4]:
                        st.markdown(f"""
                        <div class="metric-card">
                          <div class="metric-label">{m.get('label','')}</div>
                          <div class="metric-value">{m.get('value','—')}</div>
                          {unit_html}
                          {trend_html}
                        </div>""", unsafe_allow_html=True)

            # ── Charts ───────────────────────────────────────────────────────────
            chart_data = analysis.get('chart_data', {})
            has_bar  = chart_data.get('bar',  {}).get('values')
            has_pie  = chart_data.get('pie',  {}).get('values')
            has_line = chart_data.get('line', {}).get('values')

            if has_bar or has_pie or has_line:
                st.markdown('<div class="section-header">📈 Charts & Visualizations</div>', unsafe_allow_html=True)

                try:
                    import plotly.graph_objects as go
                    use_plotly = True
                except ImportError:
                    use_plotly = False

                chart_cols = st.columns(sum([bool(has_bar), bool(has_pie), bool(has_line)]) or 1)
                ci = 0

                if has_bar:
                    bar = chart_data['bar']
                    with chart_cols[ci]:
                        if use_plotly:
                            fig = go.Figure(go.Bar(
                                x=bar['labels'], y=bar['values'],
                                marker_color='#7c3aed'
                            ))
                            fig.update_layout(
                                title=bar.get('title', 'Bar Chart'),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='#c4b5fd',
                                height=300,
                                margin=dict(l=20, r=20, t=40, b=20)
                            )
                            fig.update_xaxes(color='#a0a0c0')
                            fig.update_yaxes(color='#a0a0c0', gridcolor='#2a2a4a')
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            import pandas as pd
                            df = pd.DataFrame({'Value': bar['values']}, index=bar['labels'])
                            st.bar_chart(df)
                    ci += 1

                if has_pie:
                    pie = chart_data['pie']
                    with chart_cols[ci]:
                        if use_plotly:
                            fig = go.Figure(go.Pie(
                                labels=pie['labels'], values=pie['values'],
                                hole=0.4,
                                marker_colors=['#7c3aed','#06b6d4','#4ade80','#f59e0b','#f87171','#a78bfa']
                            ))
                            fig.update_layout(
                                title=pie.get('title', 'Distribution'),
                                paper_bgcolor='rgba(0,0,0,0)',
                                font_color='#c4b5fd',
                                height=300,
                                margin=dict(l=20, r=20, t=40, b=20)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    ci += 1

                if has_line:
                    line = chart_data['line']
                    with chart_cols[ci]:
                        if use_plotly:
                            fig = go.Figure(go.Scatter(
                                x=line['labels'], y=line['values'],
                                mode='lines+markers',
                                line=dict(color='#06b6d4', width=2),
                                marker=dict(size=6, color='#7c3aed')
                            ))
                            fig.update_layout(
                                title=line.get('title', 'Trend'),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                font_color='#c4b5fd',
                                height=300,
                                margin=dict(l=20, r=20, t=40, b=20)
                            )
                            fig.update_xaxes(color='#a0a0c0')
                            fig.update_yaxes(color='#a0a0c0', gridcolor='#2a2a4a')
                            st.plotly_chart(fig, use_container_width=True)

            # ── Insights + Risk Flags ─────────────────────────────────────────────
            insights   = analysis.get('insights', [])
            risk_flags = analysis.get('risk_flags', [])

            if insights or risk_flags:
                left, right = st.columns(2)
                if insights:
                    with left:
                        st.markdown('<div class="section-header">💡 Insights</div>', unsafe_allow_html=True)
                        for ins in insights:
                            st.markdown(f'<div class="insight-item">💡 {ins}</div>', unsafe_allow_html=True)
                if risk_flags:
                    with right:
                        st.markdown('<div class="section-header">⚠️ Risk Flags</div>', unsafe_allow_html=True)
                        for risk in risk_flags:
                            st.markdown(f'<div class="risk-item">⚠️ {risk}</div>', unsafe_allow_html=True)

            # ── Key Fields Table ──────────────────────────────────────────────────
            key_fields = analysis.get('key_fields', {})
            if key_fields:
                st.markdown('<div class="section-header">🔑 Extracted Fields</div>', unsafe_allow_html=True)
                rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in key_fields.items())
                st.markdown(f'<table class="field-table">{rows}</table>', unsafe_allow_html=True)

            st.markdown("")

            # ── Actions ────────────────────────────────────────────────────────────
            st.markdown('<div class="section-header">🚀 Actions</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.button("🎨 Generate Visual Panels", use_container_width=True):
                    with st.spinner("Generating AI visuals..."):
                        images = generate_visuals(get_report(report_id))
                    st.markdown('<div class="section-header">🖼️ Generated Visuals</div>', unsafe_allow_html=True)
                    for img in images:
                        if img.get('b64'):
                            st.image(base64.b64decode(img['b64']), caption=f"Panel {img['panel']}", use_column_width=True)
                        elif img.get('error'):
                            st.warning(f"Panel {img['panel']} failed: {img['error']}")

            with col2:
                pdf_bytes = build_pdf(get_report(report_id))
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"report_{uploaded_file.name}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            with col3:
                with st.expander("🔧 View raw JSON analysis"):
                    st.json(analysis)
