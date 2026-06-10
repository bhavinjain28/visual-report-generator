import os
import json
import re
import numpy as np
import pandas as pd
import anthropic
from dotenv import load_dotenv

load_dotenv()


def _get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


# Column-role keyword map for retail detection
RETAIL_SIGNALS = {
    'revenue': ['revenue', 'sales', 'amount', 'gmv', 'turnover', 'receipts', 'total_sales', 'net_sales', 'price', 'total'],
    'product': ['product', 'item', 'sku', 'product_name', 'item_name', 'product_id', 'name', 'description'],
    'category': ['category', 'dept', 'department', 'segment', 'class', 'brand', 'type', 'group', 'section'],
    'date': ['date', 'month', 'week', 'period', 'order_date', 'sale_date', 'year', 'transaction_date'],
    'quantity': ['quantity', 'units', 'qty', 'volume', 'count', 'sold', 'units_sold'],
}


def detect_retail_csv(df: pd.DataFrame) -> dict:
    """
    Check if a DataFrame looks like retail transaction data.
    Returns {'is_retail': bool, 'column_map': {role: actual_col}}.
    Requires at least a revenue column + either product or category column.
    """
    cols_lower = {c.lower().strip(): c for c in df.columns}
    found = {}
    for role, keywords in RETAIL_SIGNALS.items():
        for kw in keywords:
            for col_lower, col_orig in cols_lower.items():
                if kw in col_lower:
                    found[role] = col_orig
                    break
            if role in found:
                break
    is_retail = 'revenue' in found and ('product' in found or 'category' in found)
    return {'is_retail': is_retail, 'column_map': found}


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce'
    )


def compute_retail_kpis(df: pd.DataFrame, column_map: dict) -> dict:
    """
    Compute retail-specific KPIs:
    - Total revenue, avg transaction
    - Revenue by category (sorted)
    - Top 5 / Bottom 5 products
    - Month-over-Month growth (if date column present)
    - Total units sold
    """
    df = df.copy()
    kpis = {}

    rev_col = column_map.get('revenue')
    cat_col = column_map.get('category')
    prod_col = column_map.get('product')
    date_col = column_map.get('date')
    qty_col = column_map.get('quantity')

    if rev_col and rev_col in df.columns:
        df[rev_col] = _coerce_numeric(df[rev_col])
        kpis['total_revenue'] = float(df[rev_col].sum())
        kpis['avg_transaction'] = float(df[rev_col].mean())
        kpis['num_transactions'] = int(df[rev_col].notna().sum())
        kpis['revenue_column'] = rev_col

    if rev_col and cat_col and cat_col in df.columns:
        rev_by_cat = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
        kpis['revenue_by_category'] = {str(k): float(v) for k, v in rev_by_cat.items()}
        if len(rev_by_cat) > 0:
            kpis['top_category'] = str(rev_by_cat.index[0])
            kpis['top_category_revenue'] = float(rev_by_cat.iloc[0])
            total = kpis.get('total_revenue', 1)
            kpis['top_category_pct'] = round(100 * float(rev_by_cat.iloc[0]) / total, 1) if total else 0

    if rev_col and prod_col and prod_col in df.columns:
        rev_by_prod = df.groupby(prod_col)[rev_col].sum().sort_values(ascending=False)
        kpis['top_products'] = {str(k): float(v) for k, v in rev_by_prod.head(5).items()}
        kpis['bottom_products'] = {str(k): float(v) for k, v in rev_by_prod.tail(5).items()}
        kpis['total_skus'] = int(len(rev_by_prod))

    if rev_col and date_col and date_col in df.columns:
        try:
            df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
            df['_month'] = df['_date'].dt.to_period('M')
            monthly = df.groupby('_month')[rev_col].sum().sort_index()
            if len(monthly) >= 2:
                mom = monthly.pct_change() * 100
                kpis['monthly_revenue'] = {str(k): float(v) for k, v in monthly.items()}
                kpis['mom_growth'] = {str(k): round(float(v), 2) for k, v in mom.dropna().items()}
                kpis['latest_mom_pct'] = round(float(mom.iloc[-1]), 2)
                kpis['latest_month'] = str(monthly.index[-1])
                kpis['prev_month'] = str(monthly.index[-2])
                kpis['prev_month_revenue'] = float(monthly.iloc[-2])
                kpis['latest_month_revenue'] = float(monthly.iloc[-1])
        except Exception:
            pass

    if qty_col and qty_col in df.columns:
        df[qty_col] = pd.to_numeric(df[qty_col], errors='coerce')
        kpis['total_units'] = float(df[qty_col].sum())

    return kpis


def detect_anomalies(df: pd.DataFrame, column_map: dict) -> list:
    """
    IQR-based outlier detection on numeric columns.
    Returns up to 20 anomaly dicts with label, value, expected range, direction.
    """
    df = df.copy()
    anomalies = []

    rev_col = column_map.get('revenue')
    prod_col = column_map.get('product')
    cat_col = column_map.get('category')

    check_cols = [rev_col] if rev_col and rev_col in df.columns else \
        df.select_dtypes(include=[np.number]).columns.tolist()

    for col in check_cols:
        if not col or col not in df.columns:
            continue
        series = _coerce_numeric(df[col]).dropna()
        if len(series) < 4:
            continue
        Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
        IQR = Q3 - Q1
        if IQR == 0:
            continue
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        df[col] = _coerce_numeric(df[col])
        outlier_mask = (df[col] < lower) | (df[col] > upper)
        for idx, row in df[outlier_mask].iterrows():
            parts = []
            if prod_col and prod_col in df.columns:
                parts.append(str(row.get(prod_col, '')))
            if cat_col and cat_col in df.columns:
                parts.append(f"[{row.get(cat_col, '')}]")
            label = " ".join(p for p in parts if p) or f"Row {idx}"
            val = float(row[col])
            anomalies.append({
                'column': col,
                'value': val,
                'expected_range': [round(float(lower), 2), round(float(upper), 2)],
                'direction': 'high' if val > upper else 'low',
                'label': label,
                'deviation_pct': round(abs(val - (upper if val > upper else lower)) / max(abs(upper - lower), 1) * 100, 1),
            })

    anomalies.sort(key=lambda x: x['deviation_pct'], reverse=True)
    return anomalies[:20]


def explain_anomalies(anomalies: list, kpis: dict) -> str:
    """Send detected anomalies to Claude Haiku for plain-English business explanation."""
    if not anomalies:
        return "No anomalies detected in this dataset."
    client = _get_client()
    prompt = f"""You are a retail data analyst. Statistical outliers were found using IQR method in retail data.

Anomalies detected:
{json.dumps(anomalies, indent=2)}

Dataset context:
- Total Revenue: {kpis.get('total_revenue', 'N/A')}
- Top Category: {kpis.get('top_category', 'N/A')}
- Latest MoM Growth: {kpis.get('latest_mom_pct', 'N/A')}%
- Total SKUs: {kpis.get('total_skus', 'N/A')}

For each anomaly write a 1-2 sentence plain-English explanation covering: what is unusual, why it might matter for a retail business, and what to investigate. Be concise and business-friendly. Number each one."""

    resp = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text.strip()


def run_rca(metric_name: str, metric_value, kpis: dict, anomalies: list, df_summary: str) -> dict:
    """
    Send metric context to Claude for a structured causal driver tree + RCA.
    Returns a dict with root_cause_summary, driver_tree, recommended_actions,
    confidence, and monitoring_metrics.
    """
    client = _get_client()

    slim_kpis = {k: v for k, v in kpis.items()
                 if k not in ('monthly_revenue', 'mom_growth', 'top_products',
                              'bottom_products', 'revenue_by_category')}

    prompt = f"""You are a senior retail data scientist performing causal Root Cause Analysis (RCA).

METRIC UNDER INVESTIGATION: {metric_name}
CURRENT VALUE: {metric_value}

CORE KPIs:
{json.dumps(slim_kpis, indent=2, default=str)}

TOP vs BOTTOM PRODUCTS:
{json.dumps({'top_5': kpis.get('top_products', {}), 'bottom_5': kpis.get('bottom_products', {})}, default=str)}

REVENUE BY CATEGORY:
{json.dumps(kpis.get('revenue_by_category', {}), default=str)}

MoM TREND:
{json.dumps(kpis.get('mom_growth', {}), default=str)}

STATISTICAL ANOMALIES (IQR-detected):
{json.dumps(anomalies[:8], indent=2)}

DATASET: {df_summary}

Build a causal driver tree explaining this metric. Return ONLY valid JSON (no markdown, no code fences):
{{
  "root_cause_summary": "2-3 sentence plain-English summary of the most likely root cause",
  "driver_tree": [
    {{
      "driver": "primary driver name",
      "impact": "high|medium|low",
      "evidence": "specific evidence from the data provided",
      "sub_drivers": [
        {{"driver": "sub-driver name", "impact": "high|medium|low", "evidence": "specific evidence"}}
      ]
    }}
  ],
  "recommended_actions": ["specific actionable recommendation for retail ops team"],
  "confidence": 0.0,
  "monitoring_metrics": ["metric name to watch going forward"]
}}"""

    resp = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            'root_cause_summary': raw[:600],
            'driver_tree': [],
            'recommended_actions': [],
            'confidence': 0.5,
            'monitoring_metrics': [],
        }
                            