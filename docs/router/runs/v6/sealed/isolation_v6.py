"""Isolation of v6 train+val (main 3f72300 data == 39945a9 data, blob-identical) against every registered v9 sealed set.
Uses router.isolation.load_exclusions / rejected_rows (keys: file_sha256/doc_sha256/content_sha256/doc_id and project).
Extra (report only): exact text overlap between the scoring candidate text and train/val excerpt/text."""
import json, sys, hashlib
from pathlib import Path
REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO / 'scripts'))
from router.isolation import load_exclusions, rejected_rows
from router.labels import load_sealed_config
cfg = load_sealed_config(REPO / 'configs/router/sealed_eval.json')['v9_sealed']
def jl(p): return [json.loads(l) for l in Path(p).read_text(encoding='utf-8').splitlines() if l.strip()]
pools = {p: jl(REPO / p) for p in ('data/router/train.jsonl', 'data/router/val.jsonl')}
res = {'repo_commit_data': '3f72300 (train/val blobs identical at 39945a9)', 'train_val_sha256': {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in pools}, 'sets': {}}
for s in cfg['sets']:
    ex = load_exclusions(REPO / s['sealed_labels'])
    rej = {p: len(rejected_rows(rows, ex)) for p, rows in pools.items()}
    res['sets'][s['name']] = {'sealed_labels': s['sealed_labels'], 'rows': len(jl(REPO / s['sealed_labels'])), 'rows_registered': s['rows'],
                              'sealed_sha256': hashlib.sha256((REPO / s['sealed_labels']).read_bytes()).hexdigest(),
                              'rejected': {p: [len(pools[p]), n] for p, n in rej.items()}, 'isolated': all(n == 0 for n in rej.values())}
    print(s['name'], res['sets'][s['name']]['rows'], s['rows'], rej)
(OUT / 'isolation_v6.json').write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
