"""
Themed, interactive Plotly chart builders for Reportly AI.
All charts share one visual language, rich hover cards, and smooth
entrance via Plotly's native transitions.
"""

import plotly.graph_objects as go

PALETTE = ['#6366f1', '#06b6d4', '#34d399', '#f59e0b', '#f87171',
           '#a78bfa', '#fb7185', '#38bdf8', '#facc15', '#4ade80']


def _colors(theme: str) -> dict:
    dark = theme == 'dark'
    return {
        'ax': '#6e7681' if dark else '#94a3b8',
        'grid': 'rgba(148,163,184,0.12)',
        'font': '#8b949e' if dark else '#64748b',
        'text': '#e6edf3' if dark else '#0f172a',
        'hover_bg': '#1c2128' if dark else '#ffffff',
        'hover_border': '#30363d' if dark else '#e2e8f0',
    }


def _base_layout(fig: go.Figure, theme: str, title: str = None, height: int = 320):
    c = _colors(theme)
    fig.update_layout(
        title=dict(text=title, font=dict(color=c['font'], size=13,
                   family='Plus Jakarta Sans, Inter, sans-serif')) if title else None,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=20, r=20, t=46 if title else 20, b=20),
        font=dict(family='Inter, sans-serif', color=c['ax'], size=12),
        hoverlabel=dict(bgcolor=c['hover_bg'], bordercolor=c['hover_border'],
                        font=dict(color=c['text'], size=12, family='Inter, sans-serif')),
        transition=dict(duration=500, easing='cubic-in-out'),
        showlegend=fig.layout.showlegend if fig.layout.showlegend is not None else False,
    )
    fig.update_xaxes(color=c['ax'], gridcolor=c['grid'], zeroline=False)
    fig.update_yaxes(color=c['ax'], gridcolor=c['grid'], zeroline=False)
    return fig


def bar_chart(labels, values, title=None, theme='light', horizontal=False, color=None):
    colors = color or [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    kwargs = dict(
        marker=dict(color=colors, line=dict(width=0), cornerradius=6),
        hovertemplate='<b>%{customdata}</b><br>%{text}<extra></extra>',
        customdata=labels,
        text=[f'{v:,.2f}'.rstrip('0').rstrip('.') for v in values],
        textposition='none',
    )
    if horizontal:
        fig = go.Figure(go.Bar(x=values, y=labels, orientation='h', **kwargs))
        fig.update_layout(yaxis=dict(autorange='reversed'))
    else:
        fig = go.Figure(go.Bar(x=labels, y=values, **kwargs))
    return _base_layout(fig, theme, title)


def donut_chart(labels, values, title=None, theme='light'):
    c = _colors(theme)
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.58,
        marker=dict(colors=PALETTE[:len(labels)], line=dict(color='rgba(0,0,0,0)', width=2)),
        textinfo='percent',
        textfont=dict(size=11, color='#ffffff'),
        hovertemplate='<b>%{label}</b><br>%{value:,.2f} (%{percent})<extra></extra>',
        pull=[0.03] + [0] * (len(labels) - 1),  # subtly lift the largest slice
        sort=True,
    ))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation='v', font=dict(size=11, color=c['ax']), x=1.02, y=0.5),
        annotations=[dict(text=f'<b>{len(labels)}</b><br><span style="font-size:10px">segments</span>',
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(size=18, color=c['text'], family='Plus Jakarta Sans, sans-serif'))],
    )
    return _base_layout(fig, theme, title)


def line_chart(labels, values, title=None, theme='light', area=True):
    fig = go.Figure(go.Scatter(
        x=labels, y=values,
        mode='lines+markers',
        line=dict(color='#06b6d4', width=2.5, shape='spline', smoothing=0.8),
        marker=dict(size=7, color='#6366f1', line=dict(color='#ffffff', width=1.5)),
        fill='tozeroy' if area else None,
        fillcolor='rgba(6,182,212,0.08)' if area else None,
        hovertemplate='<b>%{x}</b><br>%{y:,.2f}<extra></extra>',
    ))
    fig = _base_layout(fig, theme, title)
    if len(labels) > 12:
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
        fig.update_layout(height=360)
    return fig


def monthly_bar_chart(labels, values, growth_map, title=None, theme='light'):
    """Monthly revenue bars colored by MoM direction, with growth in the hover."""
    colors = ['#34d399' if growth_map.get(m, 0) >= 0 else '#f87171' for m in labels]
    hover = [f'{growth_map.get(m, 0):+.1f}% MoM' if m in growth_map else '—' for m in labels]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors, cornerradius=6),
        customdata=hover,
        hovertemplate='<b>%{x}</b><br>%{y:,.0f}<br>%{customdata}<extra></extra>',
    ))
    return _base_layout(fig, theme, title)


def gauge_chart(score: int, label: str = '', theme='light'):
    """Animated-feel health score gauge, 0-100."""
    c = _colors(theme)
    if score >= 70:
        color, zone = '#34d399', 'Strong'
    elif score >= 45:
        color, zone = '#f59e0b', 'Moderate'
    else:
        color, zone = '#f87171', 'Weak'
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=score,
        number=dict(font=dict(size=44, color=c['text'], family='Plus Jakarta Sans, sans-serif'),
                    suffix='<span style="font-size:18px;color:' + c['ax'] + '">/100</span>'),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, tickcolor=c['ax'],
                      tickfont=dict(size=10, color=c['ax'])),
            bar=dict(color=color, thickness=0.72),
            bgcolor='rgba(148,163,184,0.12)',
            borderwidth=0,
            steps=[
                dict(range=[0, 45], color='rgba(248,113,113,0.10)'),
                dict(range=[45, 70], color='rgba(245,158,11,0.10)'),
                dict(range=[70, 100], color='rgba(52,211,153,0.10)'),
            ],
            threshold=dict(line=dict(color=c['ax'], width=2), thickness=0.8, value=score),
        ),
        title=dict(text=label or zone, font=dict(size=13, color=c['font'],
                   family='Plus Jakarta Sans, sans-serif')),
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=240,
                      margin=dict(l=30, r=30, t=40, b=10))
    return fig


def radar_chart(dimensions, doc_scores, benchmark_scores, theme='light'):
    """Document vs industry-benchmark radar."""
    c = _colors(theme)
    dims = list(dimensions) + [dimensions[0]]
    doc = list(doc_scores) + [doc_scores[0]]
    bench = list(benchmark_scores) + [benchmark_scores[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=bench, theta=dims, name='Industry benchmark',
        line=dict(color='#94a3b8', width=1.5, dash='dot'),
        fill='toself', fillcolor='rgba(148,163,184,0.08)',
        hovertemplate='<b>%{theta}</b><br>Benchmark: %{r}<extra></extra>',
    ))
    fig.add_trace(go.Scatterpolar(
        r=doc, theta=dims, name='This document',
        line=dict(color='#6366f1', width=2.5),
        fill='toself', fillcolor='rgba(99,102,241,0.15)',
        marker=dict(size=6, color='#6366f1'),
        hovertemplate='<b>%{theta}</b><br>Score: %{r}<extra></extra>',
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=c['grid'],
                            tickfont=dict(size=9, color=c['ax']), linecolor='rgba(0,0,0,0)'),
            angularaxis=dict(gridcolor=c['grid'], tickfont=dict(size=11, color=c['font'],
                             family='Plus Jakarta Sans, sans-serif'), linecolor=c['grid']),
        ),
        showlegend=True,
        legend=dict(orientation='h', y=-0.12, x=0.5, xanchor='center',
                    font=dict(size=11, color=c['ax'])),
        paper_bgcolor='rgba(0,0,0,0)',
        height=380,
        margin=dict(l=60, r=60, t=30, b=40),
        hoverlabel=dict(bgcolor=c['hover_bg'], bordercolor=c['hover_border'],
                        font=dict(color=c['text'], size=12)),
    )
    return fig


PLOTLY_CONFIG = {
    'displayModeBar': 'hover',
    'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
    'displaylogo': False,
    'toImageButtonOptions': {'format': 'png', 'scale': 2},
}
