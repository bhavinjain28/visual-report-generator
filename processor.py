import os
import base64

SUPPORTED_EXTENSIONS = {'pdf', 'txt', 'md', 'markdown', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'docx', 'csv'}

IMAGE_MIME = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'webp': 'image/webp',
    'gif': 'image/gif',
}


def extract(file_path: str) -> dict:
    ext = file_path.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        return _extract_pdf(file_path)
    elif ext in IMAGE_MIME:
        return _extract_image(file_path, ext)
    elif ext == 'docx':
        return _extract_docx(file_path)
    elif ext == 'csv':
        return _extract_csv(file_path)
    elif ext in ('txt', 'md', 'markdown'):
        return _extract_text(file_path)
    else:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'unsupported', 'error': f'Unsupported: {ext}'}


def _extract_pdf(path):
    try:
        import fitz
        doc = fitz.open(path)
        text = '\n'.join(page.get_text() for page in doc)
        doc.close()

        if len(text.strip()) > 100:
            return {'text': text, 'image_b64': None, 'mime_type': None, 'method': 'pdf_text', 'error': None}

        # Scanned PDF — use vision
        doc = fitz.open(path)
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes('png')
        doc.close()
        b64 = base64.b64encode(img_bytes).decode()
        return {'text': '', 'image_b64': b64, 'mime_type': 'image/png', 'method': 'pdf_vision', 'error': None}
    except Exception as e:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'pdf_error', 'error': str(e)}


def _extract_image(path, ext):
    try:
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        return {'text': '', 'image_b64': b64, 'mime_type': IMAGE_MIME[ext], 'method': 'image_vision', 'error': None}
    except Exception as e:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'image_error', 'error': str(e)}


def _extract_docx(path):
    try:
        from docx import Document
        doc = Document(path)
        text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        return {'text': text, 'image_b64': None, 'mime_type': None, 'method': 'docx', 'error': None}
    except Exception as e:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'docx_error', 'error': str(e)}


def _extract_csv(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        return {'text': text, 'image_b64': None, 'mime_type': None, 'method': 'csv', 'error': None}
    except Exception as e:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'csv_error', 'error': str(e)}


def _extract_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
        return {'text': text, 'image_b64': None, 'mime_type': None, 'method': 'plaintext', 'error': None}
    except Exception as e:
        return {'text': '', 'image_b64': None, 'mime_type': None, 'method': 'text_error', 'error': str(e)}
