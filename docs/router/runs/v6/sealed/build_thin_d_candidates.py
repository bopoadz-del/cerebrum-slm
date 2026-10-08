"""Build scoring candidates for the thin_d sealed addendum from the source PDFs.

Same text rule as router-cr/build.py (the CR addendum candidates): pdftotext, whitespace collapsed,
OCR (pdftoppm 200 dpi + tesseract) only if the text layer is < 200 chars, then the first 6000 chars.
Each PDF is matched to a sealed row by its sha256 (== sealed file_sha256); no name decides anything.
"""
import hashlib, json, subprocess, tempfile, sys
from pathlib import Path
SRC = Path('/workspace/router-relabel-v8/score_v6/thin_d_src')
SEALED = Path(sys.argv[1])
OUT = Path(sys.argv[2])
def text_of(pdf):
    t = subprocess.run(['pdftotext', str(pdf), '-'], capture_output=True, text=True).stdout
    return ' '.join(t.split())
by = {hashlib.sha256(p.read_bytes()).hexdigest(): p for p in SRC.glob('*.pdf')}
rows = []
for line in SEALED.read_text(encoding='utf-8').splitlines():
    g = json.loads(line)
    p = by.get(g['file_sha256'])
    if p is None:
        print('MISSING', g['sheet_id']); continue
    txt = text_of(p); ocr = False
    if len(txt) < 200:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(['pdftoppm', '-r', '200', '-png', str(p), f'{td}/i'], check=True)
            tt = [subprocess.run(['tesseract', str(x), '-'], capture_output=True, text=True).stdout for x in sorted(Path(td).glob('*.png'))]
        txt = ' '.join(' '.join(tt).split()); ocr = True
    txt = txt[:6000]
    rows.append({'id': g['sheet_id'], 'sha256': g['file_sha256'], 'text_sha256': hashlib.sha256(txt.encode()).hexdigest(),
                 'source_url': g.get('source_url'), 'ocr_excerpt': ocr, 'chars': len(txt), 'text': txt})
    print(g['sheet_id'], len(txt), ocr)
OUT.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
print('rows', len(rows))
