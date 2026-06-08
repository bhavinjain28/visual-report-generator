import streamlit as st
import tempfile
import os
import base64
import json
import pandas as pd

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
from visual_gen import generate_visuals
from database import init_db, save_report, get_all_reports, get_report
from report_builder import build_pdf
from retail_analyzer import (
    detect_retail_csv, compute_retail_kpis,
    detect_anomalies, explain_anomalies, run_rca
)

# ── SVG Icon Library (Heroicons outline style) ──────────────────────────────────
IC = {
    'summary':   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16c0 1.1.9 2 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    'metrics':   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    'charts':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    'insights':  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    'risks':     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'fields':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
    'actions':   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    'retail':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
    'kpis':      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    'anomaly':   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="11"/><line x1="11" y1="14" x2="11.01" y2="14"/></svg>',
    'rca':       '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>',
    'trend_up':  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    'trend_dn':  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
    'visuals':   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
    'pin':       '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    'trophy':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 9H3a1 1 0 0 0-1 1v1a6 6 0 0 0 6 6h0a6 6 0 0 0 6-6v-1a1 1 0 0 0-1-1h-3"/><line x1="12" y1="16" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>',
    'trending_dn': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
    'tree':      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    'moon':      '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    'sun':       '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
}

# ── Theme CSS variables ──────────────────────────────────────────────────────────
THEME_VARS = {
    'light': """
:root {
  --bg: #f0f2f8;
  --surface: #ffffff;
  --surface-2: #f8fafc;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-2: #374151;
  --text-muted: #64748b;
  --text-subtle: #94a3b8;
  --accent: #4f46e5;
  --accent-h: #4338ca;
  --accent-soft: #eef2ff;
  --accent-border: #c7d2fe;
  --accent-text: #4338ca;
  --accent-dark: #1e1b4b;
  --hero-glow: radial-gradient(ellipse 80% 60% at 50% -5%, rgba(99,102,241,0.14) 0%, transparent 65%),
               radial-gradient(ellipse 40% 40% at 85% 65%, rgba(124,58,237,0.08) 0%, transparent 55%);
  --card-shadow: 0 1px 3px rgba(15,23,42,0.07), 0 4px 12px rgba(15,23,42,0.05);
  --card-shadow-hover: 0 6px 24px rgba(79,70,229,0.15), 0 2px 6px rgba(15,23,42,0.06);
  --btn-shadow: 0 2px 8px rgba(79,70,229,0.3);
  --btn-shadow-hover: 0 4px 16px rgba(79,70,229,0.42);
  --success: #059669; --success-bg: #f0fdf4; --success-border: #bbf7d0; --success-text: #065f46;
  --success-mid: #10b981; --success-light: #6ee7b7;
  --warning: #d97706; --warning-bg: #fffbeb; --warning-border: #fde68a; --warning-text: #78350f;
  --warning-mid: #f59e0b; --warning-orange: #ea580c; --warning-orange-bg: rgba(234,88,12,0.1);
  --danger:  #dc2626; --danger-bg:  #fef2f2; --danger-border:  #fecaca; --danger-text:  #991b1b;
  --info:    #2563eb; --info-bg:    #eff6ff; --info-border:    #bfdbfe; --info-text:    #1e40af;
  --info-mid: #3b82f6;
  --purple-bg: #f5f3ff; --purple-border: #ddd6fe; --purple-mid: #7c3aed;
  --navbar-border: #e2e8f0;
  --divider-from: #e2e8f0; --divider-mid: #c7d2fe; --divider-to: #a5f3fc;
}""",
    'dark': """
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface-2: #1c2128;
  --border: #30363d;
  --text: #e6edf3;
  --text-2: #c9d1d9;
  --text-muted: #8b949e;
  --text-subtle: #6e7681;
  --accent: #818cf8;
  --accent-h: #a5b4fc;
  --accent-soft: rgba(99,102,241,0.15);
  --accent-border: rgba(99,102,241,0.4);
  --accent-text: #a5b4fc;
  --accent-dark: #a5b4fc;
  --hero-glow: radial-gradient(ellipse 80% 60% at 50% -5%, rgba(99,102,241,0.2) 0%, transparent 65%),
               radial-gradient(ellipse 40% 40% at 85% 65%, rgba(124,58,237,0.12) 0%, transparent 55%);
  --card-shadow: 0 1px 3px rgba(0,0,0,0.4), 0 4px 12px rgba(0,0,0,0.3);
  --card-shadow-hover: 0 6px 24px rgba(99,102,241,0.2), 0 2px 6px rgba(0,0,0,0.4);
  --btn-shadow: 0 2px 8px rgba(99,102,241,0.35);
  --btn-shadow-hover: 0 4px 16px rgba(99,102,241,0.5);
  --success: #3fb950; --success-bg: rgba(63,185,80,0.1);  --success-border: rgba(63,185,80,0.3);  --success-text: #7ee787;
  --success-mid: #2ea043; --success-light: #56d364;
  --warning: #d29922; --warning-bg: rgba(210,153,34,0.1); --warning-border: rgba(210,153,34,0.3); --warning-text: #e3b341;
  --warning-mid: #bb8009; --warning-orange: #f0883e; --warning-orange-bg: rgba(240,136,62,0.12);
  --danger:  #f85149; --danger-bg:  rgba(248,81,73,0.1);  --danger-border:  rgba(248,81,73,0.3);  --danger-text:  #ff7b72;
  --info:    #388bfd; --info-bg:    rgba(56,139,253,0.1);  --info-border:    rgba(56,139,253,0.3);  --info-text:    #79c0ff;
  --info-mid: #58a6ff;
  --purple-bg: rgba(124,58,237,0.12); --purple-border: rgba(124,58,237,0.3); --purple-mid: #a78bfa;
  --navbar-border: #21262d;
  --divider-from: #21262d; --divider-mid: rgba(99,102,241,0.5); --divider-to: rgba(56,139,253,0.4);
}"""
}

st.set_page_config(page_title="Reportly AI", layout="wide", page_icon="📊")

init_db()

theme = st.session_state.get('theme', 'light')

# Theme vars injected first so all CSS below can use var()
st.markdown(f"<style>{THEME_VARS[theme]}</style>", unsafe_allow_html=True)

# ── Base CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=Inter:wght@400;500;600&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] > .main > .block-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
  transition: background-color 0.35s ease, color 0.35s ease;
}

[data-testid="stAppViewContainer"] > .main {
  background: var(--hero-glow), var(--bg) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }

[data-testid="block-container"] {
  padding: 0 2.5rem 5rem 2.5rem !important;
  max-width: 1200px !important;
  margin: 0 auto !important;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── Upload zone ────────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div,
[data-testid="stFileUploader"] section,
div[data-testid="stFileUploadDropzone"],
.stFileUploader > div {
  background: var(--surface) !important;
  border: 2px dashed var(--accent-border) !important;
  border-radius: 16px !important;
  padding: 2rem !important;
  box-shadow: var(--card-shadow) !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p { color: var(--text-subtle) !important; font-size: 13px !important; }
[data-testid="stFileUploaderFileName"] { color: var(--text) !important; font-weight: 500 !important; }
[data-testid="stFileUploader"] button {
  background: var(--accent) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 0.45rem 1.1rem !important;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
  background: var(--accent) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 10px !important;
  font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 0.55rem 1.25rem !important;
  letter-spacing: 0.01em !important;
  transition: background 0.2s, box-shadow 0.2s, transform 0.15s !important;
  box-shadow: var(--btn-shadow) !important;
}
.stButton > button:hover {
  background: var(--accent-h) !important;
  box-shadow: var(--btn-shadow-hover) !important;
  transform: translateY(-1px) !important;
}
/* Theme toggle button — ghost style */
.stButton[data-theme-toggle] > button,
button[data-testid="theme-toggle"] {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: 1px solid var(--border) !important;
  box-shadow: none !important;
  padding: 0.4rem 0.9rem !important;
  font-size: 12px !important;
}
.stButton[data-theme-toggle] > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
[data-testid="stDownloadButton"] > button {
  background: var(--surface) !important;
  color: var(--text-2) !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: var(--card-shadow) !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  box-shadow: var(--card-shadow-hover) !important;
  transform: translateY(-1px) !important;
}

/* ── Expander ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  box-shadow: var(--card-shadow) !important;
}
[data-testid="stExpander"] summary { color: var(--text-muted) !important; font-size: 13px !important; font-weight: 500 !important; }

/* ── Section header ─────────────────────────────────────────────────────── */
.section-header {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 2.2rem 0 1rem 0;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-header svg { color: var(--accent); opacity: 0.8; flex-shrink: 0; }
.section-header::before {
  content: '';
  display: inline-block;
  width: 3px; height: 13px;
  background: linear-gradient(180deg, var(--accent), var(--purple-mid));
  border-radius: 2px;
  flex-shrink: 0;
}

/* ── Result title & divider ─────────────────────────────────────────────── */
.result-title {
  font-size: clamp(1.4rem, 3vw, 1.9rem);
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.025em;
  margin: 1.5rem 0 0.5rem 0;
  line-height: 1.2;
}
.styled-divider {
  height: 1px;
  background: linear-gradient(90deg, var(--divider-from), var(--divider-mid) 40%, var(--divider-to) 70%, var(--divider-from));
  margin: 2rem 0;
  border: none;
}

/* ── Badges ─────────────────────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 11px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 6px;
  letter-spacing: 0.02em;
}
.badge-positive { background: var(--success-bg);  color: var(--success-text);  border: 1px solid var(--success-border); }
.badge-neutral  { background: var(--surface-2);   color: var(--text-muted);    border: 1px solid var(--border); }
.badge-negative { background: var(--danger-bg);   color: var(--danger-text);   border: 1px solid var(--danger-border); }
.badge-type     { background: var(--accent-soft); color: var(--accent-text);   border: 1px solid var(--accent-border); }
.badge-conf     { background: var(--info-bg);     color: var(--info-text);     border: 1px solid var(--info-border); }

/* ── Summary box ────────────────────────────────────────────────────────── */
.summary-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 14px;
  padding: 18px 22px;
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.75;
  margin-bottom: 1.5rem;
  box-shadow: var(--card-shadow);
}

/* ── KPI metric cards ───────────────────────────────────────────────────── */
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px 18px;
  text-align: center;
  margin-bottom: 12px;
  transition: box-shadow 0.2s, transform 0.2s;
  box-shadow: var(--card-shadow);
  position: relative;
  overflow: hidden;
}
.metric-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--purple-mid));
  border-radius: 16px 16px 0 0;
}
.metric-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-2px); }
.metric-label { color: var(--text-subtle); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 8px; }
.metric-value { color: var(--text); font-size: 26px; font-weight: 700; letter-spacing: -0.03em; line-height: 1; }
.metric-unit  { color: var(--text-subtle); font-size: 11px; margin-top: 5px; }
.trend-up   { color: var(--success); font-size: 12px; font-weight: 600; margin-top: 6px; }
.trend-down { color: var(--danger);  font-size: 12px; font-weight: 600; margin-top: 6px; }

/* ── Insight / Risk items ───────────────────────────────────────────────── */
.insight-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--info-bg);
  border: 1px solid var(--info-border);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--info-text);
  margin-bottom: 8px;
  font-size: 13.5px;
  line-height: 1.55;
}
.insight-item::before { content: '●'; color: var(--info-mid); font-size: 7px; margin-top: 5px; flex-shrink: 0; }

.risk-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--warning-bg);
  border: 1px solid var(--warning-border);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--warning-text);
  margin-bottom: 8px;
  font-size: 13.5px;
  line-height: 1.55;
}
.risk-item::before { content: '▲'; color: var(--warning-mid); font-size: 7px; margin-top: 5px; flex-shrink: 0; }

/* ── Field table ────────────────────────────────────────────────────────── */
.field-table { width: 100%; border-collapse: collapse; }
.field-table tr:last-child td { border-bottom: none; }
.field-table td { padding: 9px 14px; border-bottom: 1px solid var(--surface-2); font-size: 13px; color: var(--text-2); }
.field-table td:first-child { color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; width: 36%; }

/* ── Retail mode ────────────────────────────────────────────────────────── */
.retail-banner {
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 16px;
  padding: 16px 22px;
  margin-bottom: 1.5rem;
  display: flex; align-items: center; gap: 14px;
}
.retail-banner-icon { font-size: 28px; }
.retail-banner-text { color: var(--success-text); font-size: 15px; font-weight: 700; }
.retail-banner-sub  { color: var(--success-mid);  font-size: 12px; margin-top: 2px; }

.retail-kpi-card {
  background: var(--surface);
  border: 1px solid var(--success-border);
  border-radius: 16px;
  padding: 20px 16px;
  text-align: center;
  margin-bottom: 12px;
  box-shadow: var(--card-shadow);
  position: relative; overflow: hidden;
}
.retail-kpi-card::after {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--success-mid), var(--success));
  border-radius: 16px 16px 0 0;
}
.retail-kpi-label { color: var(--success-light); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 8px; }
.retail-kpi-value { color: var(--success-text); font-size: 24px; font-weight: 700; letter-spacing: -0.03em; }
.retail-kpi-sub   { color: var(--success-mid); font-size: 11px; margin-top: 5px; }
.mom-positive { color: var(--success); font-weight: 700; }
.mom-negative { color: var(--danger);  font-weight: 700; }
.product-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 14px;
  border-bottom: 1px solid var(--success-bg);
  font-size: 13px;
}
.product-row:last-child { border-bottom: none; }
.product-name { color: var(--success-text); }
.product-rev  { color: var(--success-mid); font-weight: 600; }

/* ── Anomaly cards ──────────────────────────────────────────────────────── */
.anomaly-card {
  background: var(--surface);
  border: 1px solid var(--warning-border);
  border-left: 3px solid var(--warning-mid);
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;
  transition: box-shadow 0.2s;
  box-shadow: var(--card-shadow);
}
.anomaly-card:hover { box-shadow: 0 6px 16px var(--warning-orange-bg); }
.anomaly-label  { color: var(--warning-text); font-size: 13.5px; font-weight: 600; }
.anomaly-detail { color: var(--warning);      font-size: 12px; margin-top: 4px; }
.anomaly-direction-high { color: var(--warning-orange); font-size: 10px; font-weight: 700; letter-spacing: 0.05em; margin-top: 5px; }
.anomaly-direction-low  { color: var(--info);            font-size: 10px; font-weight: 700; letter-spacing: 0.05em; margin-top: 5px; }
.anomaly-explanation {
  background: var(--warning-bg);
  border: 1px solid var(--warning-border);
  border-left: 3px solid var(--warning-mid);
  border-radius: 14px;
  padding: 16px 20px;
  color: var(--warning-text);
  font-size: 13.5px;
  line-height: 1.7;
  margin-top: 12px;
  white-space: pre-wrap;
}

/* ── RCA / Driver tree ──────────────────────────────────────────────────── */
.rca-summary {
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  border-left: 3px solid var(--accent);
  border-radius: 14px;
  padding: 18px 22px;
  color: var(--accent-dark);
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 1.25rem;
}
.driver-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 10px;
  box-shadow: var(--card-shadow);
  transition: box-shadow 0.2s;
}
.driver-card:hover { box-shadow: var(--card-shadow-hover); }
.driver-card-sub {
  background: var(--purple-bg);
  border: 1px solid var(--purple-border);
  border-radius: 10px;
  padding: 10px 14px;
  margin: 10px 0 0 24px;
}
.driver-name     { color: var(--accent-dark); font-size: 15px; font-weight: 700; margin-bottom: 5px; }
.driver-evidence { color: var(--accent-text); font-size: 13px; line-height: 1.5; }
.driver-name-sub     { color: var(--accent-text); font-size: 12.5px; font-weight: 600; margin-bottom: 3px; }
.driver-evidence-sub { color: var(--purple-mid);  font-size: 12px; }
.impact-high   { background: var(--danger-bg);  color: var(--danger);  border: 1px solid var(--danger-border);  padding: 2px 10px; border-radius: 100px; font-size: 10px; font-weight: 700; margin-left: 8px; }
.impact-medium { background: var(--warning-bg); color: var(--warning); border: 1px solid var(--warning-border); padding: 2px 10px; border-radius: 100px; font-size: 10px; font-weight: 700; margin-left: 8px; }
.impact-low    { background: var(--success-bg); color: var(--success); border: 1px solid var(--success-border); padding: 2px 10px; border-radius: 100px; font-size: 10px; font-weight: 700; margin-left: 8px; }
.rca-action {
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 10px;
  padding: 9px 16px;
  color: var(--success-text);
  font-size: 13px;
  margin-bottom: 7px;
}
.rca-monitor {
  display: inline-block;
  background: var(--accent-soft);
  color: var(--accent-text);
  border: 1px solid var(--accent-border);
  padding: 4px 14px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 500;
  margin: 4px 4px 4px 0;
}
.rca-confidence { color: var(--text-subtle); font-size: 11px; margin-top: 8px; text-align: right; }

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  [data-testid="block-container"] { padding: 0 1rem 3rem 1rem !important; }
  .hero-title { font-size: 2rem !important; }
  .hero-sub { font-size: 0.95rem !important; }
  .metric-value { font-size: 22px; }
  .retail-kpi-value { font-size: 20px; }
}
@media (max-width: 480px) {
  .hero-title { font-size: 1.6rem !important; }
  .badge { font-size: 10px; padding: 3px 8px; }
  .driver-card-sub { margin-left: 8px; }
  .metric-card { padding: 16px 12px; }
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ──────────────────────────────────────────────────────────
for key in ('rca_result', 'anomaly_explanation', 'current_file'):
    if key not in st.session_state:
        st.session_state[key] = None

# ── Navbar ───────────────────────────────────────────────────────────────────────
nav_left, nav_mid, nav_right = st.columns([5, 3, 2])

with nav_left:
    st.markdown(
        f"""<div style="padding:1rem 0 0.8rem 0;border-bottom:1px solid var(--navbar-border);">
          <span style="font-size:16px;font-weight:800;color:var(--text);letter-spacing:-0.04em;font-family:'Plus Jakarta Sans',sans-serif;">
            Reportly<span style="color:var(--accent);">.</span>ai
          </span>
        </div>""",
        unsafe_allow_html=True
    )

with nav_mid:
    st.markdown(
        f"""<div style="padding:1rem 0 0.8rem 0;border-bottom:1px solid var(--navbar-border);
                       display:flex;align-items:center;justify-content:center;">
          <span style="font-size:11px;font-weight:600;color:var(--accent-text);background:var(--accent-soft);
                       border:1px solid var(--accent-border);border-radius:100px;padding:4px 14px;letter-spacing:0.04em;">
            AI Analytics
          </span>
        </div>""",
        unsafe_allow_html=True
    )

with nav_right:
    # Spacer to align toggle button with navbar
    st.markdown('<div style="padding-top:0.65rem;border-bottom:1px solid var(--navbar-border);padding-bottom:0.4rem;">', unsafe_allow_html=True)
    toggle_label = "◑  Dark" if theme == 'light' else "◐  Light"
    if st.button(toggle_label, key='theme_btn'):
        st.session_state.theme = 'dark' if theme == 'light' else 'light'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:3.5rem 1rem 2.5rem 1rem;">
  <h1 style="font-size:clamp(2rem,5vw,3.4rem);font-weight:800;letter-spacing:-0.04em;
             line-height:1.1;color:var(--text);margin:0 0 1rem 0;
             font-family:'Plus Jakarta Sans',-apple-system,sans-serif;">
    Turn any document into<br>
    <span style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 background-clip:text;">actionable intelligence</span>
  </h1>
  <p style="font-size:1.05rem;color:var(--text-muted);max-width:500px;
            margin:0 auto 0 auto;line-height:1.7;font-weight:400;">
    Upload a PDF, CSV, image or text file — get instant KPIs, anomaly detection,
    visual charts, and AI-driven root cause analysis.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────────
_, upload_col, _ = st.columns([0.5, 9, 0.5])
with upload_col:
    uploaded_file = st.file_uploader(
        "upload",
        type=["pdf", "txt", "csv", "jpg", "png"],
        label_visibility="collapsed"
    )

st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

if uploaded_file:
    # Reset session state when a new file is uploaded
    if st.session_state.current_file != uploaded_file.name:
        st.session_state.current_file = uploaded_file.name
        st.session_state.rca_result = None
        st.session_state.anomaly_explanation = None

    ext = uploaded_file.name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    with st.spinner("Extracting content..."):
        extracted = extract(tmp_path)

    # ── Retail Mode: detect on CSV files ─────────────────────────────────────
    retail_data = None
    if ext == 'csv':
        try:
            df = pd.read_csv(tmp_path)
            detection = detect_retail_csv(df)
            if detection['is_retail']:
                col_map = detection['column_map']
                kpis = compute_retail_kpis(df, col_map)
                anomalies = detect_anomalies(df, col_map)
                retail_data = {
                    'df': df,
                    'column_map': col_map,
                    'kpis': kpis,
                    'anomalies': anomalies,
                }
        except Exception as e:
            st.warning(f"Retail mode: {e}")

    if extracted.get('error'):
        st.error(f"Extraction failed: {extracted['error']}")
    else:
        with st.spinner("Analyzing with AI..."):
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

            # ── Title + Badges ──────────────────────────────────────────────
            sentiment = analysis.get('sentiment', 'Neutral')
            conf = analysis.get('confidence', 0)
            doc_type = analysis.get('document_type', 'Document')
            badge_class = {
                'Positive': 'badge-positive',
                'Negative': 'badge-negative',
            }.get(sentiment, 'badge-neutral')
            sent_icon = {'Positive': '▲', 'Negative': '▼'}.get(sentiment, '●')

            st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="result-title">{analysis.get("title", uploaded_file.name)}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="margin:8px 0 20px 0">'
                f'<span class="badge badge-type">{doc_type}</span>'
                f'<span class="badge {badge_class}">{sent_icon} {sentiment}</span>'
                f'<span class="badge badge-conf">Confidence: {int(conf*100)}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ═══════════════════════════════════════════════════════════════
            # RETAIL MODE PANEL (injected before regular summary)
            # ═══════════════════════════════════════════════════════════════
            if retail_data:
                kpis = retail_data['kpis']
                col_map = retail_data['column_map']

                st.markdown(f"""
<div class="retail-banner">
  <span class="retail-banner-icon">{IC['retail']}</span>
  <div>
    <div class="retail-banner-text">Retail Intelligence Mode Activated</div>
    <div class="retail-banner-sub">Retail CSV detected — showing category revenue, MoM growth, top/bottom products &amp; anomaly radar</div>
  </div>
</div>""", unsafe_allow_html=True)

                # ── Retail KPI cards ────────────────────────────────────────
                st.markdown(f'<div class="section-header">{IC["kpis"]} Retail KPIs</div>', unsafe_allow_html=True)

                mom_pct = kpis.get('latest_mom_pct')
                mom_html = ''
                if mom_pct is not None:
                    mom_class = 'mom-positive' if mom_pct >= 0 else 'mom-negative'
                    mom_arrow = '▲' if mom_pct >= 0 else '▼'
                    mom_html = f'<div class="{mom_class}">{mom_arrow} {abs(mom_pct):.1f}% MoM</div>'

                total_rev = kpis.get('total_revenue', 0)
                rev_display = f"₹{total_rev/1e7:.2f}Cr" if total_rev >= 1e7 else \
                              f"₹{total_rev/1e5:.2f}L" if total_rev >= 1e5 else \
                              f"₹{total_rev:,.0f}"

                avg_tx = kpis.get('avg_transaction', 0)
                avg_display = f"₹{avg_tx:,.2f}"

                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    st.markdown(f"""
<div class="retail-kpi-card">
  <div class="retail-kpi-label">Total Revenue</div>
  <div class="retail-kpi-value">{rev_display}</div>
  {mom_html}
</div>""", unsafe_allow_html=True)
                with r2:
                    st.markdown(f"""
<div class="retail-kpi-card">
  <div class="retail-kpi-label">Avg. Transaction</div>
  <div class="retail-kpi-value">{avg_display}</div>
  <div class="retail-kpi-sub">{kpis.get('num_transactions', 0):,} transactions</div>
</div>""", unsafe_allow_html=True)
                with r3:
                    top_cat = kpis.get('top_category', '—')
                    top_cat_pct = kpis.get('top_category_pct', 0)
                    st.markdown(f"""
<div class="retail-kpi-card">
  <div class="retail-kpi-label">Top Category</div>
  <div class="retail-kpi-value" style="font-size:18px">{top_cat}</div>
  <div class="retail-kpi-sub">{top_cat_pct:.1f}% of revenue</div>
</div>""", unsafe_allow_html=True)
                with r4:
                    total_skus = kpis.get('total_skus', '—')
                    total_units = kpis.get('total_units')
                    units_html = f'<div class="retail-kpi-sub">{total_units:,.0f} units sold</div>' if total_units else ''
                    st.markdown(f"""
<div class="retail-kpi-card">
  <div class="retail-kpi-label">Total SKUs</div>
  <div class="retail-kpi-value">{total_skus}</div>
  {units_html}
</div>""", unsafe_allow_html=True)

                # ── Revenue by Category + MoM chart ───────────────────────
                chart_left, chart_right = st.columns(2)

                with chart_left:
                    rev_by_cat = kpis.get('revenue_by_category', {})
                    if rev_by_cat:
                        import plotly.graph_objects as go
                        cats = list(rev_by_cat.keys())
                        vals = list(rev_by_cat.values())
                        is_dark = (theme == 'dark')
                        fig = go.Figure(go.Bar(
                            x=vals, y=cats, orientation='h',
                            marker_color='#4ade80' if is_dark else '#22c55e',
                            marker_line_color='#16a34a',
                            marker_line_width=1,
                        ))
                        fig.update_layout(
                            title=dict(text="Revenue by Category", font=dict(color='#64748b' if not is_dark else '#8b949e', size=13)),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            height=300,
                            margin=dict(l=10, r=10, t=40, b=20),
                            yaxis=dict(autorange='reversed'),
                        )
                        ax_color = '#94a3b8' if not is_dark else '#6e7681'
                        fig.update_xaxes(color=ax_color, gridcolor='rgba(148,163,184,0.15)')
                        fig.update_yaxes(color=ax_color)
                        st.plotly_chart(fig, use_container_width=True)

                with chart_right:
                    monthly_rev = kpis.get('monthly_revenue', {})
                    if monthly_rev:
                        import plotly.graph_objects as go
                        months = list(monthly_rev.keys())
                        m_vals = list(monthly_rev.values())
                        mom_growth = kpis.get('mom_growth', {})
                        colors = ['#4ade80' if mom_growth.get(m, 0) >= 0 else '#f87171' for m in months]
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(
                            x=months, y=m_vals,
                            marker_color=colors,
                            name='Monthly Revenue',
                        ))
                        is_dark = (theme == 'dark')
                        ax_color = '#94a3b8' if not is_dark else '#6e7681'
                        fig2.update_layout(
                            title=dict(text="Monthly Revenue (MoM)", font=dict(color='#64748b' if not is_dark else '#8b949e', size=13)),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            height=300,
                            margin=dict(l=10, r=10, t=40, b=20),
                        )
                        fig2.update_xaxes(color=ax_color, gridcolor='rgba(148,163,184,0.15)')
                        fig2.update_yaxes(color=ax_color, gridcolor='rgba(148,163,184,0.15)')
                        st.plotly_chart(fig2, use_container_width=True)

                # ── Top / Bottom Products ──────────────────────────────────
                if kpis.get('top_products') or kpis.get('bottom_products'):
                    prod_left, prod_right = st.columns(2)
                    with prod_left:
                        st.markdown(f'<div class="section-header">{IC["trophy"]} Top 5 Products by Revenue</div>', unsafe_allow_html=True)
                        for name, rev in (kpis.get('top_products') or {}).items():
                            rev_fmt = f"₹{rev/1e5:.2f}L" if rev >= 1e5 else f"₹{rev:,.0f}"
                            st.markdown(f"""
<div class="product-row">
  <span class="product-name">{name}</span>
  <span class="product-rev">{rev_fmt}</span>
</div>""", unsafe_allow_html=True)
                    with prod_right:
                        st.markdown(f'<div class="section-header">{IC["trending_dn"]} Bottom 5 Products by Revenue</div>', unsafe_allow_html=True)
                        for name, rev in (kpis.get('bottom_products') or {}).items():
                            rev_fmt = f"₹{rev/1e5:.2f}L" if rev >= 1e5 else f"₹{rev:,.0f}"
                            st.markdown(f"""
<div class="product-row" style="border-bottom:1px solid var(--danger-bg);">
  <span style="color:var(--danger-text);">{name}</span>
  <span style="color:var(--danger);font-weight:600;">{rev_fmt}</span>
</div>""", unsafe_allow_html=True)

            # ── Regular Summary ──────────────────────────────────────────────
            if analysis.get('summary'):
                st.markdown(f'<div class="section-header">{IC["summary"]} Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="summary-box">{analysis["summary"]}</div>', unsafe_allow_html=True)

            # ── KPI Metric Cards ─────────────────────────────────────────────
            metrics = analysis.get('key_metrics', [])
            if metrics:
                st.markdown(f'<div class="section-header">{IC["metrics"]} Key Metrics</div>', unsafe_allow_html=True)
                cols = st.columns(min(len(metrics), 4))
                for i, m in enumerate(metrics[:8]):
                    trend_html = ''
                    if m.get('trend') == 'up':
                        trend_html = f'<div class="trend-up">{IC["trend_up"]} Up</div>'
                    elif m.get('trend') == 'down':
                        trend_html = f'<div class="trend-down">{IC["trend_dn"]} Down</div>'
                    unit_html = f'<div class="metric-unit">{m["unit"]}</div>' if m.get('unit') else ''
                    with cols[i % 4]:
                        st.markdown(f"""
<div class="metric-card">
<div class="metric-label">{m.get('label','')}</div>
<div class="metric-value">{m.get('value','—')}</div>
{unit_html}
{trend_html}
</div>""", unsafe_allow_html=True)

            # ── Charts ───────────────────────────────────────────────────────
            chart_data = analysis.get('chart_data', {})
            has_bar = chart_data.get('bar', {}).get('values')
            has_pie = chart_data.get('pie', {}).get('values')
            has_line = chart_data.get('line', {}).get('values')

            if has_bar or has_pie or has_line:
                st.markdown(f'<div class="section-header">{IC["charts"]} Charts &amp; Visualizations</div>', unsafe_allow_html=True)
                try:
                    import plotly.graph_objects as go
                    use_plotly = True
                except ImportError:
                    use_plotly = False

                is_dark = (theme == 'dark')
                ax_color  = '#94a3b8' if not is_dark else '#6e7681'
                grid_color = 'rgba(148,163,184,0.15)'
                font_color = '#64748b' if not is_dark else '#8b949e'

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
                                title=dict(text=bar.get('title','Bar Chart'), font=dict(color=font_color, size=13)),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=300,
                                margin=dict(l=20, r=20, t=40, b=20)
                            )
                            fig.update_xaxes(color=ax_color, gridcolor=grid_color)
                            fig.update_yaxes(color=ax_color, gridcolor=grid_color)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            df_bar = pd.DataFrame({'Value': bar['values']}, index=bar['labels'])
                            st.bar_chart(df_bar)
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
                                title=dict(text=pie.get('title','Distribution'), font=dict(color=font_color, size=13)),
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color=ax_color),
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
                                title=dict(text=line.get('title','Trend'), font=dict(color=font_color, size=13)),
                                paper_bgcolor='rgba(0,0,0,0)',
                                plot_bgcolor='rgba(0,0,0,0)',
                                height=300,
                                margin=dict(l=20, r=20, t=40, b=20)
                            )
                            fig.update_xaxes(color=ax_color, gridcolor=grid_color)
                            fig.update_yaxes(color=ax_color, gridcolor=grid_color)
                            st.plotly_chart(fig, use_container_width=True)

            # ── Insights + Risk Flags ────────────────────────────────────────
            insights = analysis.get('insights', [])
            risk_flags = analysis.get('risk_flags', [])

            if insights or risk_flags:
                left, right = st.columns(2)
                if insights:
                    with left:
                        st.markdown(f'<div class="section-header">{IC["insights"]} Insights</div>', unsafe_allow_html=True)
                        for ins in insights:
                            st.markdown(f'<div class="insight-item">{ins}</div>', unsafe_allow_html=True)
                if risk_flags:
                    with right:
                        st.markdown(f'<div class="section-header">{IC["risks"]} Risk Flags</div>', unsafe_allow_html=True)
                        for risk in risk_flags:
                            st.markdown(f'<div class="risk-item">{risk}</div>', unsafe_allow_html=True)

            # ═══════════════════════════════════════════════════════════════
            # ANOMALY DETECTION SECTION
            # ═══════════════════════════════════════════════════════════════
            if retail_data and retail_data['anomalies']:
                anomalies = retail_data['anomalies']
                st.markdown(
                    f'<div class="section-header">{IC["anomaly"]} Anomaly Radar &mdash; {len(anomalies)} outlier(s) detected</div>',
                    unsafe_allow_html=True
                )

                a_cols = st.columns(min(len(anomalies), 3))
                for i, a in enumerate(anomalies):
                    dir_class = 'anomaly-direction-high' if a['direction'] == 'high' else 'anomaly-direction-low'
                    dir_label = f"↑ Abnormally HIGH (+{a.get('deviation_pct', 0):.0f}% above fence)" \
                        if a['direction'] == 'high' \
                        else f"↓ Abnormally LOW ({a.get('deviation_pct', 0):.0f}% below fence)"
                    val_fmt = f"{a['value']:,.2f}"
                    range_fmt = f"[{a['expected_range'][0]:,.2f} – {a['expected_range'][1]:,.2f}]"
                    with a_cols[i % 3]:
                        st.markdown(f"""
<div class="anomaly-card">
  <div class="anomaly-label">{a['label']}</div>
  <div class="anomaly-detail">{a['column']}: <b>{val_fmt}</b> — Expected {range_fmt}</div>
  <div class="{dir_class}">{dir_label}</div>
</div>""", unsafe_allow_html=True)

                if st.button("Explain Anomalies with AI", use_container_width=False):
                    with st.spinner("Asking Claude to explain anomalies..."):
                        st.session_state.anomaly_explanation = explain_anomalies(
                            anomalies, retail_data['kpis']
                        )

                if st.session_state.anomaly_explanation:
                    st.markdown(
                        f'<div class="anomaly-explanation">{st.session_state.anomaly_explanation}</div>',
                        unsafe_allow_html=True
                    )

            elif retail_data and not retail_data['anomalies']:
                st.markdown(f'<div class="section-header">{IC["anomaly"]} Anomaly Radar</div>', unsafe_allow_html=True)
                st.success("No statistical outliers detected — all values within IQR bounds.")

            # ── Key Fields Table ─────────────────────────────────────────────
            key_fields = analysis.get('key_fields', {})
            if key_fields:
                st.markdown(f'<div class="section-header">{IC["fields"]} Extracted Fields</div>', unsafe_allow_html=True)
                rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in key_fields.items())
                st.markdown(f'<table class="field-table">{rows}</table>', unsafe_allow_html=True)
            st.markdown("")

            # ── Actions ──────────────────────────────────────────────────────
            st.markdown(f'<div class="section-header">{IC["actions"]} Actions</div>', unsafe_allow_html=True)

            if retail_data:
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            else:
                col1, col2, col3 = st.columns([1, 1, 2])
                col4 = None

            with col1:
                if st.button("Generate Visual Panels", use_container_width=True):
                    with st.spinner("Asking Claude to design infographics..."):
                        images = generate_visuals(get_report(report_id))
                    st.markdown(f'<div class="section-header">{IC["visuals"]} AI-Generated Infographics</div>', unsafe_allow_html=True)
                    for img in images:
                        if img.get('svg'):
                            st.markdown(f"**Panel {img['panel']}: {img.get('label','')}**")
                            st.markdown(img['svg'], unsafe_allow_html=True)
                            st.markdown("")
                        elif img.get('error'):
                            st.warning(f"Panel {img['panel']} failed: {img['error']}")

            with col2:
                report_for_pdf = get_report(report_id)
                if retail_data:
                    report_for_pdf['retail_kpis'] = retail_data['kpis']
                    report_for_pdf['retail_anomalies'] = retail_data['anomalies']
                if st.session_state.rca_result:
                    report_for_pdf['retail_rca'] = st.session_state.rca_result
                pdf_bytes = build_pdf(report_for_pdf)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"report_{uploaded_file.name}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            with col3:
                with st.expander("View raw JSON analysis"):
                    st.json(analysis)

            # ═══════════════════════════════════════════════════════════════
            # AI DRIVER TREE / RCA SECTION
            # ═══════════════════════════════════════════════════════════════
            if retail_data and col4 is not None:
                kpis = retail_data['kpis']
                anomalies = retail_data['anomalies']

                if kpis.get('latest_mom_pct') is not None:
                    rca_metric = f"Revenue MoM Growth ({kpis.get('latest_month', 'latest')})"
                    rca_value = f"{kpis['latest_mom_pct']:.2f}%"
                elif kpis.get('total_revenue') is not None:
                    rca_metric = "Total Revenue"
                    rca_value = kpis['total_revenue']
                else:
                    rca_metric = retail_data['column_map'].get('revenue', 'Key Metric')
                    rca_value = "N/A"

                df_summary = (
                    f"{len(retail_data['df'])} rows × {len(retail_data['df'].columns)} cols. "
                    f"Columns: {', '.join(retail_data['df'].columns.tolist()[:12])}"
                )

                with col4:
                    if st.button("Why did this happen? (RCA)", use_container_width=True):
                        with st.spinner("Building causal driver tree..."):
                            st.session_state.rca_result = run_rca(
                                rca_metric, rca_value, kpis, anomalies, df_summary
                            )

            if st.session_state.rca_result:
                rca = st.session_state.rca_result
                st.markdown(f'<div class="section-header">{IC["rca"]} AI Root Cause Analysis &mdash; Causal Driver Tree</div>', unsafe_allow_html=True)

                if rca.get('root_cause_summary'):
                    st.markdown(
                        f'<div class="rca-summary"><b>Root Cause:</b> {rca["root_cause_summary"]}</div>',
                        unsafe_allow_html=True
                    )

                if rca.get('driver_tree'):
                    st.markdown("**Causal Driver Tree:**")
                    for driver in rca['driver_tree']:
                        impact = driver.get('impact', 'medium').lower()
                        impact_badge = f'<span class="impact-{impact}">{impact.upper()}</span>'
                        sub_html = ""
                        for sd in driver.get('sub_drivers', []):
                            sd_impact = sd.get('impact', 'low').lower()
                            sub_html += (
                                f'<div class="driver-card-sub">'
                                f'<div class="driver-name-sub">↳ {sd.get("driver", "—")} '
                                f'<span class="impact-{sd_impact}">{sd_impact.upper()}</span></div>'
                                f'<div class="driver-evidence-sub">{sd.get("evidence", "")}</div>'
                                f'</div>'
                            )
                        st.markdown(
                            f'<div class="driver-card">'
                            f'<div class="driver-name">{driver.get("driver", "—")}{impact_badge}</div>'
                            f'<div class="driver-evidence">{driver.get("evidence", "")}</div>'
                            f'{sub_html}'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                if rca.get('recommended_actions'):
                    st.markdown("**Recommended Actions:**")
                    for i, action in enumerate(rca['recommended_actions'], 1):
                        st.markdown(f'<div class="rca-action">✓ {i}. {action}</div>', unsafe_allow_html=True)

                if rca.get('monitoring_metrics'):
                    st.markdown("**Monitor Going Forward:**")
                    badges = "".join(f'<span class="rca-monitor">{m}</span>' for m in rca['monitoring_metrics'])
                    st.markdown(badges, unsafe_allow_html=True)

                conf_pct = int(rca.get('confidence', 0.5) * 100)
                st.markdown(f'<div class="rca-confidence">AI confidence: {conf_pct}%</div>', unsafe_allow_html=True)
