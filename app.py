import streamlit as st
import tempfile
import os
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
from analyzer import analyze, classify
from industry_knowledge import get_profile
from visual_gen import generate_visuals
from database import init_db, save_report, get_all_reports, get_report
from report_builder import build_pdf
from retail_analyzer import (
    detect_retail_csv, compute_retail_kpis,
    detect_anomalies, explain_anomalies, run_rca
)
import charts
from charts import PLOTLY_CONFIG

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
    'trophy':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 9H3a1 1 0 0 0-1 1v1a6 6 0 0 0 6 6h0a6 6 0 0 0 6-6v-1a1 1 0 0 0-1-1h-3"/><line x1="12" y1="16" x2="12" y2="22"/><line x1="8" y1="22" x2="16" y2="22"/></svg>',
    'trending_dn': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>',
    'health':    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    'benchmark': '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    'oppty':     '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/><path d="M2 18h2"/><path d="M20 18h2"/><path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/><path d="m8 6 4-4 4 4"/><path d="M16 18a4 4 0 0 0-8 0"/></svg>',
    'recs':      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    'glossary':  '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
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
  --shimmer-base: #eef0f6; --shimmer-hi: #f9fafc;
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
  --shimmer-base: #1c2128; --shimmer-hi: #262c36;
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

/* ── Animations ─────────────────────────────────────────────────────────── */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes gradientShift {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
@keyframes shimmer {
  0%   { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}
@keyframes pulseSoft {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.25); }
  50%      { box-shadow: 0 0 0 6px rgba(99,102,241,0); }
}
@keyframes valueReveal {
  from { opacity: 0; transform: translateY(8px); filter: blur(3px); }
  to   { opacity: 1; transform: translateY(0); filter: blur(0); }
}

.anim { animation: fadeInUp 0.55s cubic-bezier(0.21, 0.6, 0.35, 1) both; }
.d0 { animation-delay: 0.00s; } .d1 { animation-delay: 0.07s; }
.d2 { animation-delay: 0.14s; } .d3 { animation-delay: 0.21s; }
.d4 { animation-delay: 0.28s; } .d5 { animation-delay: 0.35s; }
.d6 { animation-delay: 0.42s; } .d7 { animation-delay: 0.49s; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.001s !important; transition-duration: 0.001s !important; }
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
  transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s !important;
}
[data-testid="stFileUploader"] section:hover {
  border-color: var(--accent) !important;
  box-shadow: var(--card-shadow-hover) !important;
  transform: translateY(-1px);
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
  transition: transform 0.15s, box-shadow 0.2s !important;
}
[data-testid="stFileUploader"] button:hover { transform: translateY(-1px); box-shadow: var(--btn-shadow-hover) !important; }

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
.stButton > button:active { transform: translateY(0) scale(0.98) !important; }
[data-testid="stDownloadButton"] > button {
  background: var(--surface) !important;
  color: var(--text-2) !important;
  border: 1.5px solid var(--border) !important;
  box-shadow: var(--card-shadow) !important;
  transition: border-color 0.2s, color 0.2s, box-shadow 0.2s, transform 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  box-shadow: var(--card-shadow-hover) !important;
  transform: translateY(-1px) !important;
}

/* ── Status / spinner ───────────────────────────────────────────────────── */
[data-testid="stStatusWidget"], [data-testid="stStatus"] { border-radius: 12px !important; }
div[data-testid="stExpander"] details,
[data-testid="stStatus"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}

/* ── Expander ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  box-shadow: var(--card-shadow) !important;
}
[data-testid="stExpander"] summary { color: var(--text-muted) !important; font-size: 13px !important; font-weight: 500 !important; }

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 4px;
  box-shadow: var(--card-shadow);
}
.stTabs [data-baseweb="tab"] {
  border-radius: 9px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  transition: background 0.2s, color 0.2s;
}
.stTabs [aria-selected="true"] {
  background: var(--accent-soft) !important;
  color: var(--accent-text) !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { animation: fadeIn 0.4s ease both; padding-top: 0.6rem; }

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
  animation: fadeInUp 0.5s ease both;
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
  animation: fadeInUp 0.5s ease both;
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
  animation: fadeIn 0.6s ease both;
}
.badge-positive { background: var(--success-bg);  color: var(--success-text);  border: 1px solid var(--success-border); }
.badge-neutral  { background: var(--surface-2);   color: var(--text-muted);    border: 1px solid var(--border); }
.badge-negative { background: var(--danger-bg);   color: var(--danger-text);   border: 1px solid var(--danger-border); }
.badge-type     { background: var(--accent-soft); color: var(--accent-text);   border: 1px solid var(--accent-border); }
.badge-conf     { background: var(--info-bg);     color: var(--info-text);     border: 1px solid var(--info-border); }
.badge-model    { background: var(--purple-bg);   color: var(--purple-mid);    border: 1px solid var(--purple-border); }

/* ── Industry banner ────────────────────────────────────────────────────── */
.industry-banner {
  position: relative;
  display: flex; align-items: center; gap: 16px;
  background: var(--surface);
  border: 1px solid var(--accent-border);
  border-radius: 16px;
  padding: 18px 22px;
  margin: 0.5rem 0 1.5rem 0;
  box-shadow: var(--card-shadow);
  overflow: hidden;
}
.industry-banner::before {
  content: '';
  position: absolute; top: 0; left: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, var(--accent), var(--purple-mid), #06b6d4);
  background-size: 100% 300%;
  animation: gradientShift 4s ease infinite;
}
.industry-icon {
  font-size: 30px;
  width: 54px; height: 54px;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  border-radius: 14px;
  flex-shrink: 0;
  animation: pulseSoft 3s ease infinite;
}
.industry-name { color: var(--text); font-size: 16px; font-weight: 700; font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.02em; }
.industry-sub  { color: var(--text-muted); font-size: 12.5px; margin-top: 3px; line-height: 1.5; }

/* ── Executive takeaway ─────────────────────────────────────────────────── */
.exec-takeaway {
  background: linear-gradient(135deg, var(--accent-soft), var(--purple-bg));
  border: 1px solid var(--accent-border);
  border-radius: 16px;
  padding: 20px 26px;
  margin-bottom: 1.25rem;
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.55;
  color: var(--accent-dark);
  letter-spacing: -0.01em;
  position: relative;
}
.exec-takeaway::before {
  content: 'KEY TAKEAWAY';
  display: block;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: var(--accent-text);
  opacity: 0.75;
  margin-bottom: 7px;
}

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
  transition: box-shadow 0.25s, transform 0.25s, border-color 0.25s;
  box-shadow: var(--card-shadow);
  position: relative;
  overflow: hidden;
}
.metric-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--purple-mid), #06b6d4);
  background-size: 200% 100%;
  border-radius: 16px 16px 0 0;
  transition: background-position 0.6s ease;
}
.metric-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-3px); border-color: var(--accent-border); }
.metric-card:hover::after { background-position: 100% 0; }
.metric-label { color: var(--text-subtle); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 8px; }
.metric-value { color: var(--text); font-size: 26px; font-weight: 700; letter-spacing: -0.03em; line-height: 1; animation: valueReveal 0.7s cubic-bezier(0.21,0.6,0.35,1) both; animation-delay: inherit; }
.metric-unit  { color: var(--text-subtle); font-size: 11px; margin-top: 5px; }
.trend-up   { color: var(--success); font-size: 12px; font-weight: 600; margin-top: 6px; }
.trend-down { color: var(--danger);  font-size: 12px; font-weight: 600; margin-top: 6px; }

.bench-chip {
  display: inline-block;
  margin-top: 8px;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: help;
}
.bench-above   { background: var(--success-bg); color: var(--success); border: 1px solid var(--success-border); }
.bench-at      { background: var(--info-bg);    color: var(--info);    border: 1px solid var(--info-border); }
.bench-below   { background: var(--danger-bg);  color: var(--danger);  border: 1px solid var(--danger-border); }
.bench-unknown { background: var(--surface-2);  color: var(--text-subtle); border: 1px solid var(--border); }

/* ── Insight / Risk / Opportunity items ─────────────────────────────────── */
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
  transition: transform 0.2s, box-shadow 0.2s;
}
.insight-item:hover { transform: translateX(3px); }
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
  transition: transform 0.2s;
}
.risk-item:hover { transform: translateX(3px); }
.risk-item::before { content: '▲'; color: var(--warning-mid); font-size: 7px; margin-top: 5px; flex-shrink: 0; }

.oppty-item {
  display: flex; align-items: flex-start; gap: 10px;
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 12px;
  padding: 12px 16px;
  color: var(--success-text);
  margin-bottom: 8px;
  font-size: 13.5px;
  line-height: 1.55;
  transition: transform 0.2s;
}
.oppty-item:hover { transform: translateX(3px); }
.oppty-item::before { content: '◆'; color: var(--success-mid); font-size: 8px; margin-top: 4px; flex-shrink: 0; }

/* ── Recommendation cards ───────────────────────────────────────────────── */
.rec-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 10px;
  box-shadow: var(--card-shadow);
  transition: box-shadow 0.2s, transform 0.2s;
  display: flex; align-items: flex-start; gap: 12px;
}
.rec-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-2px); }
.rec-num {
  width: 26px; height: 26px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-soft);
  color: var(--accent-text);
  border: 1px solid var(--accent-border);
  border-radius: 8px;
  font-size: 12px; font-weight: 700;
  font-family: 'Plus Jakarta Sans', sans-serif;
}
.rec-action    { color: var(--text); font-size: 13.5px; font-weight: 600; line-height: 1.5; }
.rec-rationale { color: var(--text-muted); font-size: 12px; margin-top: 3px; line-height: 1.5; }

/* ── Glossary ───────────────────────────────────────────────────────────── */
.glossary-term { color: var(--accent-text); font-size: 13px; font-weight: 700; }
.glossary-def  { color: var(--text-muted);  font-size: 12.5px; line-height: 1.6; margin: 2px 0 10px 0; }

/* ── Field table ────────────────────────────────────────────────────────── */
.field-table { width: 100%; border-collapse: collapse; animation: fadeIn 0.6s ease both; }
.field-table tr:last-child td { border-bottom: none; }
.field-table td { padding: 9px 14px; border-bottom: 1px solid var(--surface-2); font-size: 13px; color: var(--text-2); }
.field-table td:first-child { color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; width: 36%; }
.field-table tr { transition: background 0.15s; }
.field-table tr:hover { background: var(--surface-2); }

/* ── Retail mode ────────────────────────────────────────────────────────── */
.retail-banner {
  background: var(--success-bg);
  border: 1px solid var(--success-border);
  border-radius: 16px;
  padding: 16px 22px;
  margin-bottom: 1.5rem;
  display: flex; align-items: center; gap: 14px;
  animation: fadeInUp 0.5s ease both;
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
  transition: box-shadow 0.25s, transform 0.25s;
}
.retail-kpi-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-3px); }
.retail-kpi-card::after {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--success-mid), var(--success));
  border-radius: 16px 16px 0 0;
}
.retail-kpi-label { color: var(--success-light); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 8px; }
.retail-kpi-value { color: var(--success-text); font-size: 24px; font-weight: 700; letter-spacing: -0.03em; animation: valueReveal 0.7s ease both; }
.retail-kpi-sub   { color: var(--success-mid); font-size: 11px; margin-top: 5px; }
.mom-positive { color: var(--success); font-weight: 700; }
.mom-negative { color: var(--danger);  font-weight: 700; }
.product-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 14px;
  border-bottom: 1px solid var(--success-bg);
  font-size: 13px;
  transition: background 0.15s, transform 0.15s;
}
.product-row:hover { background: var(--surface-2); transform: translateX(2px); }
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
  transition: box-shadow 0.2s, transform 0.2s;
  box-shadow: var(--card-shadow);
}
.anomaly-card:hover { box-shadow: 0 6px 16px var(--warning-orange-bg); transform: translateY(-2px); }
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
  animation: fadeInUp 0.5s ease both;
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
  animation: fadeInUp 0.5s ease both;
}
.driver-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 20px;
  margin-bottom: 10px;
  box-shadow: var(--card-shadow);
  transition: box-shadow 0.2s, transform 0.2s;
  animation: fadeInUp 0.5s ease both;
}
.driver-card:hover { box-shadow: var(--card-shadow-hover); transform: translateY(-2px); }
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

/* ── Hero ───────────────────────────────────────────────────────────────── */
.hero-gradient-text {
  background: linear-gradient(120deg, #4f46e5, #7c3aed, #06b6d4, #4f46e5);
  background-size: 280% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientShift 7s ease infinite;
}

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  [data-testid="block-container"] { padding: 0 1rem 3rem 1rem !important; }
  .hero-title { font-size: 2rem !important; }
  .hero-sub { font-size: 0.95rem !important; }
  .metric-value { font-size: 22px; }
  .retail-kpi-value { font-size: 20px; }
  .exec-takeaway { font-size: 15px; padding: 16px 18px; }
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
for key in ('rca_result', 'anomaly_explanation', 'current_file',
            'analysis', 'extracted', 'retail_data', 'report_id', 'visual_panels'):
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
            Industry-Aware AI Analytics
          </span>
        </div>""",
        unsafe_allow_html=True
    )

with nav_right:
    st.markdown('<div style="padding-top:0.65rem;border-bottom:1px solid var(--navbar-border);padding-bottom:0.4rem;">', unsafe_allow_html=True)
    toggle_label = "◑  Dark" if theme == 'light' else "◐  Light"
    if st.button(toggle_label, key='theme_btn'):
        st.session_state.theme = 'dark' if theme == 'light' else 'light'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:3.5rem 1rem 2.5rem 1rem;" class="anim">
  <h1 class="hero-title" style="font-size:clamp(2rem,5vw,3.4rem);font-weight:800;letter-spacing:-0.04em;
             line-height:1.1;color:var(--text);margin:0 0 1rem 0;
             font-family:'Plus Jakarta Sans',-apple-system,sans-serif;">
    Turn any document into<br>
    <span class="hero-gradient-text">actionable intelligence</span>
  </h1>
  <p class="hero-sub" style="font-size:1.05rem;color:var(--text-muted);max-width:560px;
            margin:0 auto 0 auto;line-height:1.7;font-weight:400;">
    Upload a PDF, CSV, image or text file — the AI detects your industry, benchmarks your
    numbers against it, scores overall health, and builds interactive visual analytics.
  </p>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────────
_, upload_col, _ = st.columns([0.5, 9, 0.5])
with upload_col:
    uploaded_file = st.file_uploader(
        "upload",
        type=["pdf", "txt", "csv", "jpg", "png", "docx", "pptx"],
        label_visibility="collapsed"
    )

st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE (runs once per file, cached in session state)
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    with st.status("🔍 Analyzing your document...", expanded=True) as status:
        st.write("📄 Extracting content...")
        extracted = extract(tmp_path)
        if extracted.get('error'):
            status.update(label="Extraction failed", state="error")
            st.error(f"Extraction failed: {extracted['error']}")
            return None

        # Retail mode detection (CSV only)
        retail_data = None
        if ext == 'csv':
            try:
                try:
                    df = pd.read_csv(tmp_path, encoding='utf-8')
                except UnicodeDecodeError:
                    # Non-UTF-8 file (e.g. Excel exports with £/€ in Latin-1/Windows-1252)
                    df = pd.read_csv(tmp_path, encoding='latin-1')
                detection = detect_retail_csv(df)
                if detection['is_retail']:
                    st.write("🛒 Retail dataset detected — computing KPIs & scanning for anomalies...")
                    col_map = detection['column_map']
                    retail_data = {
                        'df': df,
                        'column_map': col_map,
                        'kpis': compute_retail_kpis(df, col_map),
                        'anomalies': detect_anomalies(df, col_map),
                    }
            except Exception as e:
                st.warning(f"Retail mode: {e}")

        st.write("🧭 Identifying industry & document type...")
        cls = classify(extracted, uploaded_file.name)
        profile = get_profile(cls['industry'])
        st.write(f"{profile['icon']} **{profile['name']}** detected — applying industry benchmarks & risk framework...")

        st.write("🧠 Running deep AI analysis (this is the smart part)...")
        analysis = analyze(extracted, uploaded_file.name, classification=cls)

        if 'error' in analysis:
            status.update(label="Analysis failed", state="error")
            st.error(f"Analysis failed: {analysis['error']}")
            if 'raw' in analysis:
                with st.expander("Raw AI response"):
                    st.code(analysis['raw'])
            return None

        report_id = save_report(
            filename=uploaded_file.name,
            file_type=ext,
            file_size=os.path.getsize(tmp_path),
            analysis=analysis,
            extraction_method=extracted.get('method', 'unknown')
        )
        status.update(label=f"✅ Analysis complete — {profile['name']} intelligence applied", state="complete", expanded=False)

    return {
        'extracted': extracted,
        'analysis': analysis,
        'retail_data': retail_data,
        'report_id': report_id,
    }


if uploaded_file:
    # Run the (expensive) pipeline only when a new file arrives —
    # button clicks and reruns reuse the cached result.
    if st.session_state.current_file != uploaded_file.name or st.session_state.analysis is None:
        st.session_state.current_file = uploaded_file.name
        st.session_state.rca_result = None
        st.session_state.anomaly_explanation = None
        st.session_state.visual_panels = None
        result = run_pipeline(uploaded_file)
        if result:
            st.session_state.analysis = result['analysis']
            st.session_state.extracted = result['extracted']
            st.session_state.retail_data = result['retail_data']
            st.session_state.report_id = result['report_id']
        else:
            st.session_state.analysis = None

    analysis = st.session_state.analysis
    retail_data = st.session_state.retail_data
    report_id = st.session_state.report_id

    if analysis:
        # ── Title + Badges ──────────────────────────────────────────────
        sentiment = analysis.get('sentiment', 'Neutral')
        conf = analysis.get('confidence', 0)
        doc_type = analysis.get('document_type', 'Document')
        badge_class = {
            'Positive': 'badge-positive',
            'Negative': 'badge-negative',
        }.get(sentiment, 'badge-neutral')
        sent_icon = {'Positive': '▲', 'Negative': '▼'}.get(sentiment, '●')
        model_used = analysis.get('analysis_model', '')
        model_label = 'Sonnet · deep analysis' if 'sonnet' in model_used else 'Haiku · fast analysis'

        st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-title">{analysis.get("title", uploaded_file.name)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="margin:8px 0 20px 0">'
            f'<span class="badge badge-type">{doc_type}</span>'
            f'<span class="badge {badge_class}">{sent_icon} {sentiment}</span>'
            f'<span class="badge badge-conf">Confidence: {int(conf*100)}%</span>'
            f'<span class="badge badge-model">⚡ {model_label}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Industry Intelligence Banner ────────────────────────────────
        ind_name = analysis.get('industry_name', 'General Business')
        ind_icon = analysis.get('industry_icon', '📄')
        ind_conf = int(analysis.get('industry_confidence', 0.5) * 100)
        st.markdown(f"""
<div class="industry-banner anim">
  <div class="industry-icon">{ind_icon}</div>
  <div>
    <div class="industry-name">{ind_name} Intelligence</div>
    <div class="industry-sub">Industry detected with {ind_conf}% confidence — domain KPIs,
    benchmark ranges and risk framework applied to this analysis</div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Executive Takeaway ──────────────────────────────────────────
        if analysis.get('executive_takeaway'):
            st.markdown(f'<div class="exec-takeaway anim d1">{analysis["executive_takeaway"]}</div>',
                        unsafe_allow_html=True)

        # ── Health Score + Benchmark Radar ──────────────────────────────
        bench = analysis.get('benchmark_comparison') or []
        has_radar = len(bench) >= 3
        if analysis.get('health_score') is not None:
            st.markdown(f'<div class="section-header">{IC["health"]} Document Health &amp; Industry Benchmark</div>', unsafe_allow_html=True)
            if has_radar:
                g_col, r_col = st.columns([2, 3])
            else:
                g_col, r_col = st.columns([2, 3])
            with g_col:
                fig = charts.gauge_chart(analysis['health_score'],
                                         analysis.get('health_label', ''), theme)
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            with r_col:
                if has_radar:
                    dims = [b.get('dimension', '?') for b in bench]
                    doc_scores = [b.get('document_score', 0) for b in bench]
                    bench_scores = [b.get('industry_benchmark', 50) for b in bench]
                    fig = charts.radar_chart(dims, doc_scores, bench_scores, theme)
                    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
                elif analysis.get('summary'):
                    st.markdown(f'<div class="summary-box" style="margin-top:1.4rem">{analysis["summary"]}</div>', unsafe_allow_html=True)
            if has_radar:
                with st.expander("How were these benchmark scores judged?"):
                    for b in bench:
                        st.markdown(
                            f"**{b.get('dimension','')}** — document {b.get('document_score',0)} vs "
                            f"benchmark {b.get('industry_benchmark',50)}: {b.get('comment','')}"
                        )

        # ═══════════════════════════════════════════════════════════════
        # RETAIL MODE PANEL
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
<div class="retail-kpi-card anim d0">
  <div class="retail-kpi-label">Total Revenue</div>
  <div class="retail-kpi-value">{rev_display}</div>
  {mom_html}
</div>""", unsafe_allow_html=True)
            with r2:
                st.markdown(f"""
<div class="retail-kpi-card anim d1">
  <div class="retail-kpi-label">Avg. Transaction</div>
  <div class="retail-kpi-value">{avg_display}</div>
  <div class="retail-kpi-sub">{kpis.get('num_transactions', 0):,} transactions</div>
</div>""", unsafe_allow_html=True)
            with r3:
                top_cat = kpis.get('top_category', '—')
                top_cat_pct = kpis.get('top_category_pct', 0)
                st.markdown(f"""
<div class="retail-kpi-card anim d2">
  <div class="retail-kpi-label">Top Category</div>
  <div class="retail-kpi-value" style="font-size:18px">{top_cat}</div>
  <div class="retail-kpi-sub">{top_cat_pct:.1f}% of revenue</div>
</div>""", unsafe_allow_html=True)
            with r4:
                total_skus = kpis.get('total_skus', '—')
                total_units = kpis.get('total_units')
                units_html = f'<div class="retail-kpi-sub">{total_units:,.0f} units sold</div>' if total_units else ''
                st.markdown(f"""
<div class="retail-kpi-card anim d3">
  <div class="retail-kpi-label">Total SKUs</div>
  <div class="retail-kpi-value">{total_skus}</div>
  {units_html}
</div>""", unsafe_allow_html=True)

            # ── Revenue by Category + MoM chart ───────────────────────
            chart_left, chart_right = st.columns(2)

            with chart_left:
                rev_by_cat = kpis.get('revenue_by_category', {})
                if rev_by_cat:
                    fig = charts.bar_chart(
                        list(rev_by_cat.keys()), list(rev_by_cat.values()),
                        title="Revenue by Category", theme=theme, horizontal=True,
                    )
                    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

            with chart_right:
                monthly_rev = kpis.get('monthly_revenue', {})
                if monthly_rev:
                    fig2 = charts.monthly_bar_chart(
                        list(monthly_rev.keys()), list(monthly_rev.values()),
                        kpis.get('mom_growth', {}),
                        title="Monthly Revenue (MoM)", theme=theme,
                    )
                    st.plotly_chart(fig2, use_container_width=True, config=PLOTLY_CONFIG)

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

        # ── Summary ──────────────────────────────────────────────────────
        if analysis.get('summary') and (not analysis.get('health_score') or len(bench) >= 3):
            st.markdown(f'<div class="section-header">{IC["summary"]} Summary</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="summary-box anim">{analysis["summary"]}</div>', unsafe_allow_html=True)

        # ── KPI Metric Cards (benchmark-aware) ──────────────────────────
        metrics = analysis.get('key_metrics', [])
        if metrics:
            st.markdown(f'<div class="section-header">{IC["metrics"]} Key Metrics <span style="text-transform:none;letter-spacing:0;font-weight:500;">— vs industry benchmarks</span></div>', unsafe_allow_html=True)
            cols = st.columns(min(len(metrics), 4))
            bench_labels = {
                'above': ('▲ ABOVE BENCHMARK', 'bench-above'),
                'at':    ('● AT BENCHMARK', 'bench-at'),
                'below': ('▼ BELOW BENCHMARK', 'bench-below'),
            }
            for i, m in enumerate(metrics[:8]):
                trend_html = ''
                if m.get('trend') == 'up':
                    trend_html = f'<div class="trend-up">{IC["trend_up"]} Up</div>'
                elif m.get('trend') == 'down':
                    trend_html = f'<div class="trend-down">{IC["trend_dn"]} Down</div>'
                unit_html = f'<div class="metric-unit">{m["unit"]}</div>' if m.get('unit') else ''
                b_status = (m.get('benchmark_status') or 'unknown').lower()
                b_context = (m.get('context') or '').replace('"', '&quot;')
                bench_html = ''
                if b_status in bench_labels:
                    label, cls_name = bench_labels[b_status]
                    bench_html = f'<div class="bench-chip {cls_name}" title="{b_context}">{label}</div>'
                with cols[i % 4]:
                    st.markdown(f"""
<div class="metric-card anim d{i % 8}">
<div class="metric-label">{m.get('label','')}</div>
<div class="metric-value">{m.get('value','—')}</div>
{unit_html}
{trend_html}
{bench_html}
</div>""", unsafe_allow_html=True)

        # ── Charts (interactive, tabbed) ─────────────────────────────────
        chart_data = analysis.get('chart_data', {})
        bar = chart_data.get('bar', {}) or {}
        pie = chart_data.get('pie', {}) or {}
        line = chart_data.get('line', {}) or {}
        has_bar = bool(bar.get('values'))
        has_pie = bool(pie.get('values'))
        has_line = bool(line.get('values'))

        if has_bar or has_pie or has_line:
            st.markdown(f'<div class="section-header">{IC["charts"]} Interactive Charts &amp; Visualizations</div>', unsafe_allow_html=True)

            available = []
            if has_bar:  available.append(('📊 ' + (bar.get('title') or 'Comparison'), 'bar'))
            if has_pie:  available.append(('🍩 ' + (pie.get('title') or 'Distribution'), 'pie'))
            if has_line: available.append(('📈 ' + (line.get('title') or 'Trend'), 'line'))

            if len(available) > 1:
                tabs = st.tabs([a[0] for a in available])
                tab_map = dict(zip([a[1] for a in available], tabs))
            else:
                tab_map = {available[0][1]: st.container()}

            if has_bar:
                with tab_map['bar']:
                    fig = charts.bar_chart(bar['labels'], bar['values'],
                                           title=bar.get('title'), theme=theme)
                    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            if has_pie:
                with tab_map['pie']:
                    fig = charts.donut_chart(pie['labels'], pie['values'],
                                             title=pie.get('title'), theme=theme)
                    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            if has_line:
                with tab_map['line']:
                    fig = charts.line_chart(line['labels'], line['values'],
                                            title=line.get('title'), theme=theme)
                    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # ── Insights / Risks / Opportunities ─────────────────────────────
        insights = analysis.get('insights', [])
        risk_flags = analysis.get('risk_flags', [])
        opportunities = analysis.get('opportunities', [])

        if insights or risk_flags or opportunities:
            n_cols = sum([bool(insights), bool(risk_flags), bool(opportunities)])
            cols = st.columns(n_cols)
            ci = 0
            if insights:
                with cols[ci]:
                    st.markdown(f'<div class="section-header">{IC["insights"]} Insights</div>', unsafe_allow_html=True)
                    for j, ins in enumerate(insights):
                        st.markdown(f'<div class="insight-item anim d{j % 8}">{ins}</div>', unsafe_allow_html=True)
                ci += 1
            if risk_flags:
                with cols[ci]:
                    st.markdown(f'<div class="section-header">{IC["risks"]} Risk Flags</div>', unsafe_allow_html=True)
                    for j, risk in enumerate(risk_flags):
                        st.markdown(f'<div class="risk-item anim d{j % 8}">{risk}</div>', unsafe_allow_html=True)
                ci += 1
            if opportunities:
                with cols[ci]:
                    st.markdown(f'<div class="section-header">{IC["oppty"]} Opportunities</div>', unsafe_allow_html=True)
                    for j, opp in enumerate(opportunities):
                        st.markdown(f'<div class="oppty-item anim d{j % 8}">{opp}</div>', unsafe_allow_html=True)

        # ── Recommendations ──────────────────────────────────────────────
        recs = analysis.get('recommendations', [])
        if recs:
            st.markdown(f'<div class="section-header">{IC["recs"]} Recommended Actions <span style="text-transform:none;letter-spacing:0;font-weight:500;">— prioritized</span></div>', unsafe_allow_html=True)
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            recs_sorted = sorted(recs, key=lambda r: priority_order.get(r.get('priority', 'medium'), 1))
            for i, r in enumerate(recs_sorted, 1):
                pr = r.get('priority', 'medium')
                rationale_html = f'<div class="rec-rationale">{r["rationale"]}</div>' if r.get('rationale') else ''
                st.markdown(f"""
<div class="rec-card anim d{(i-1) % 8}">
  <div class="rec-num">{i}</div>
  <div style="flex:1">
    <div class="rec-action">{r.get('action','')}<span class="impact-{pr}">{pr.upper()}</span></div>
    {rationale_html}
  </div>
</div>""", unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════
        # ANOMALY DETECTION SECTION (retail)
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
<div class="anomaly-card anim d{i % 8}">
  <div class="anomaly-label">{a['label']}</div>
  <div class="anomaly-detail">{a['column']}: <b>{val_fmt}</b> — Expected {range_fmt}</div>
  <div class="{dir_class}">{dir_label}</div>
</div>""", unsafe_allow_html=True)

            if st.button("✨ Explain Anomalies with AI", use_container_width=False):
                with st.spinner("Asking the AI to explain anomalies..."):
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

        # ── Key Fields + Glossary ────────────────────────────────────────
        key_fields = analysis.get('key_fields', {})
        glossary = analysis.get('glossary', {})

        if key_fields:
            st.markdown(f'<div class="section-header">{IC["fields"]} Extracted Fields</div>', unsafe_allow_html=True)
            rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in key_fields.items())
            st.markdown(f'<table class="field-table">{rows}</table>', unsafe_allow_html=True)

        if glossary:
            with st.expander(f"📖 Industry jargon explained ({len(glossary)} terms)"):
                for term, definition in glossary.items():
                    st.markdown(
                        f'<div class="glossary-term">{term}</div>'
                        f'<div class="glossary-def">{definition}</div>',
                        unsafe_allow_html=True
                    )
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
                with st.spinner("Designing infographic panels..."):
                    st.session_state.visual_panels = generate_visuals(get_report(report_id))

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

        if st.session_state.visual_panels:
            st.markdown(f'<div class="section-header">{IC["visuals"]} AI-Generated Infographics</div>', unsafe_allow_html=True)
            for img in st.session_state.visual_panels:
                if img.get('svg'):
                    st.markdown(f"**Panel {img['panel']}: {img.get('label','')}**")
                    st.markdown(img['svg'], unsafe_allow_html=True)
                    st.markdown("")
                elif img.get('error'):
                    st.warning(f"Panel {img['panel']} failed: {img['error']}")

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
