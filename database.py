import sqlite3
import json
import csv
import io
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / 'reports.db'


def _conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                document_type TEXT,
                title TEXT,
                summary TEXT,
                key_metrics TEXT,
                key_fields TEXT,
                insights TEXT,
                risk_flags TEXT,
                sentiment TEXT,
                confidence REAL,
                chart_data TEXT,
                infographic_prompt TEXT,
                extraction_method TEXT,
                success INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        # Migration: store complete analysis JSON (industry intelligence fields etc.)
        try:
            conn.execute('ALTER TABLE reports ADD COLUMN full_analysis TEXT')
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.commit()


def save_report(filename, file_type, file_size, analysis, extraction_method):
    with _conn() as conn:
        cursor = conn.execute('''
            INSERT INTO reports
            (filename, file_type, file_size, document_type, title, summary,
             key_metrics, key_fields, insights, risk_flags, sentiment, confidence,
             chart_data, infographic_prompt, extraction_method, success, full_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            file_type,
            file_size,
            analysis.get('document_type', 'Unknown'),
            analysis.get('title', filename),
            analysis.get('summary', ''),
            json.dumps(analysis.get('key_metrics', [])),
            json.dumps(analysis.get('key_fields', {})),
            json.dumps(analysis.get('insights', [])),
            json.dumps(analysis.get('risk_flags', [])),
            analysis.get('sentiment', 'Neutral'),
            analysis.get('confidence', 0.5),
            json.dumps(analysis.get('chart_data', {})),
            analysis.get('infographic_prompt', ''),
            extraction_method,
            0 if 'error' in analysis else 1,
            json.dumps(analysis)
        ))
        conn.commit()
        return cursor.lastrowid


def get_report(report_id):
    with _conn() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
        if not row:
            return None
        return _deserialize(dict(row))


def get_all_reports(page=1, per_page=20):
    offset = (page - 1) * per_page
    with _conn() as conn:
        total = conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
        rows = conn.execute(
            'SELECT * FROM reports ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (per_page, offset)
        ).fetchall()
        return {
            'total': total,
            'page': page,
            'per_page': per_page,
            'reports': [_deserialize(dict(r)) for r in rows]
        }


def get_stats():
    with _conn() as conn:
        total = conn.execute('SELECT COUNT(*) FROM reports').fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE date(created_at) = date('now')"
        ).fetchone()[0]
        flagged = conn.execute(
            "SELECT COUNT(*) FROM reports WHERE json_array_length(risk_flags) > 0"
        ).fetchone()[0]
        types_seen = conn.execute(
            "SELECT COUNT(DISTINCT document_type) FROM reports"
        ).fetchone()[0]

        # Sentiment breakdown
        sentiments = conn.execute(
            "SELECT sentiment, COUNT(*) as cnt FROM reports GROUP BY sentiment"
        ).fetchall()

        # By doc type
        by_type = conn.execute(
            "SELECT document_type, COUNT(*) as cnt FROM reports GROUP BY document_type ORDER BY cnt DESC LIMIT 8"
        ).fetchall()

        # Daily trend (last 14 days)
        daily = conn.execute("""
            SELECT date(created_at) as day, COUNT(*) as cnt
            FROM reports
            WHERE created_at >= date('now', '-14 days')
            GROUP BY date(created_at)
            ORDER BY day
        """).fetchall()

        # Confidence by type
        conf_by_type = conn.execute("""
            SELECT document_type, AVG(confidence) as avg_conf
            FROM reports GROUP BY document_type ORDER BY avg_conf DESC LIMIT 6
        """).fetchall()

        return {
            'total': total,
            'today': today,
            'flagged': flagged,
            'types_seen': types_seen,
            'sentiment_breakdown': [dict(r) for r in sentiments],
            'by_type': [dict(r) for r in by_type],
            'daily_trend': [dict(r) for r in daily],
            'confidence_by_type': [dict(r) for r in conf_by_type]
        }


def export_csv():
    with _conn() as conn:
        rows = conn.execute('SELECT * FROM reports ORDER BY created_at DESC').fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Filename', 'Type', 'Doc Type', 'Title', 'Sentiment',
                     'Confidence', 'Risk Flags', 'Insights', 'Created At'])
    for row in rows:
        r = dict(row)
        writer.writerow([
            r['id'], r['filename'], r['file_type'], r['document_type'],
            r['title'], r['sentiment'], r['confidence'],
            len(json.loads(r['risk_flags'] or '[]')),
            len(json.loads(r['insights'] or '[]')),
            r['created_at']
        ])
    return output.getvalue()


def _deserialize(row):
    for field in ('key_metrics', 'key_fields', 'insights', 'risk_flags', 'chart_data'):
        if isinstance(row.get(field), str):
            try:
                row[field] = json.loads(row[field])
            except Exception:
                row[field] = [] if field != 'key_fields' else {}
    # Merge full analysis JSON (industry intelligence fields) if present
    if row.get('full_analysis'):
        try:
            full = json.loads(row['full_analysis'])
            for k, v in full.items():
                row.setdefault(k, v)
        except Exception:
            pass
        row.pop('full_analysis', None)
    return row
