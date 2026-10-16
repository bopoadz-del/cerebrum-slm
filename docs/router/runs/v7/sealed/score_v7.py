"""Score a selected router v7-series checkpoint ONCE on every registered v9 sealed set (v5_retick, v8_retick, cr, thin_c, thin_d,
web_f; combined 312), then the name-blind check once.

Same logic as docs/router/runs/v6/sealed/score_v6_v9.py: same prompt (router.teacher_label.prompt_for(labels), system sha256 b1ac9472...),
sampling (max_tokens 32, temperature 0, top_p 1, seed 0, no thinking), parser (router.train_router._as_label, v9 exact aliases), gate
(evaluate_sealed_gate_v8, gate v2 + MIN_SEALED_PER_LABEL=12) and blanker (scripts/router/name_blind.py, PR #50). Only the checkpoint
(read from the run's epoch_choice.json), the sets (all six) and OUT change. Owner order 2026-10-08: no pre-run note. Each phase refuses
a second run; a resume only fills rows missing after failed calls. Never prints secrets.
Usage: score_v7.py {score|blind} --variant v7 --repo <merged main copy> --run-dir <training run dir>
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAIN_SYSTEM_SHA256 = 'b1ac9472219a4bea8b0447c2418854a85d60bcb7f154eff2252c7ef8718e3879'


def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding='utf-8').splitlines() if l.strip()]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_tree(path: Path) -> str:
    entries = []
    for child in path.iterdir():
        if child.name in ('.git', '__pycache__', '.pytest_cache'):
            continue
        if child.is_dir():
            entries.append((child.name + '/', b'40000 ' + child.name.encode() + b'\0' + bytes.fromhex(git_tree(child))))
        else:
            data = child.read_bytes()
            mode = b'100755' if os.access(child, os.X_OK) else b'100644'
            h = hashlib.sha1(b'blob %d\0' % len(data) + data).digest()
            entries.append((child.name, mode + b' ' + child.name.encode() + b'\0' + h))
    body = b''.join(e for _, e in sorted(entries, key=lambda x: x[0].encode()))
    return hashlib.sha1(b'tree %d\0' % len(body) + body).hexdigest()


def precision_table(gold, pred, labels):
    out = {}
    for lab in labels:
        n = sum(g == lab for g in gold); p = sum(x == lab for x in pred); tp = sum(g == lab and x == lab for g, x in zip(gold, pred))
        out[lab] = {'n': n, 'predicted': p, 'tp': tp, 'recall': (tp / n) if n else None, 'precision': (tp / p) if p else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['dry', 'score', 'blind'])
    ap.add_argument('--variant', required=True)
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--expect-tree', required=True)
    a = ap.parse_args()
    OUT = HERE / f'out_{a.variant}'
    OUT.mkdir(parents=True, exist_ok=True)
    log = open(OUT / 'score.log', 'a', encoding='utf-8')

    def say(*x):
        s = ' '.join(str(i) for i in x)
        print(s, flush=True); log.write(s + '\n'); log.flush()

    if a.phase == 'dry' and not (a.run_dir / 'epoch_choice.json').exists():
        CKPT = None
    else:
        choice = json.loads((a.run_dir / 'epoch_choice.json').read_text(encoding='utf-8'))
        if choice['run'] != a.variant or choice['sealed_scored'] is not False or choice['sealed_read'] is not False:
            say('WALL: epoch choice is not an unscored choice for this variant'); return 3
        CKPT = choice['chosen_checkpoint']
    if a.phase != 'dry':
        marker = OUT / f'RUN_STARTED_{a.phase}.json'
        partial = OUT / f'{a.phase}_partial.jsonl'
        final = OUT / ('sealed_scores.json' if a.phase == 'score' else 'name_blind.json')
        resume = False
        if marker.exists():
            if final.exists() or not partial.exists():
                say(f'WALL: phase {a.phase} already started; no re-runs.'); return 3
            resume = True
        if a.phase == 'blind' and not (OUT / 'sealed_scores.json').exists():
            say('WALL: blind phase needs the recorded score first'); return 3
    REPO = a.repo
    tree = git_tree(REPO)
    if tree != a.expect_tree:
        say(f'WALL: repo tree {tree[:7]} is not the expected merged tree {a.expect_tree[:7]}'); return 3
    sys.path.insert(0, str(REPO / 'scripts'))
    sys.path.insert(0, str(HERE.parent / 'box'))
    sys.path.insert(0, str(HERE.parent / 'driver_v7'))
    from router.labels import load_labels, load_sealed_config
    from router.teacher_label import prompt_for
    from router.content import content_text
    import router.train_router as tr
    import router.name_blind as nbm
    from router.sealed_gate import evaluate_sealed_gate_v8, macro_recall, MIN_SEALED_PER_LABEL
    from sealed_sources import sealed_items, check_candidates
    check_candidates()
    cfg = load_sealed_config(REPO / 'configs/router/sealed_eval.json')
    v9 = cfg['v9_sealed']
    for item in v9['sets']:
        p = REPO / item['sealed_labels']
        side = (p.parent / 'sealed_labels.jsonl.sha256').read_text(encoding='utf-8').split()[0]
        if sha(p.read_bytes()) != side or len(jl(p)) != item['rows']:
            say(f"WALL: seal mismatch {item['sealed_labels']}"); return 3
    order = [s['name'] for s in v9['sets']]
    labels = load_labels(REPO / v9['labels_file'])
    assert len(labels) == 22
    mcf = bool(cfg['sealed_gate'].get('majority_class_fail', cfg['majority_class_fail']))
    lora = json.loads((REPO / 'configs/lora/qwen3-4b-router-r16.json').read_text(encoding='utf-8'))
    system = prompt_for(labels)
    if sha(system.encode()) != TRAIN_SYSTEM_SHA256:
        say('WALL: system prompt differs from the router prompt'); return 3
    blind_src = REPO / 'scripts/router/name_blind.py'
    items_by_set = sealed_items(REPO, content_text)
    rows = {}
    for k in order:
        lst = []
        for it in items_by_set[k]:
            text = it['text']
            if not text:
                say(f"WALL: empty text {it['sheet_id']}"); return 3
            if a.phase == 'blind':
                text, nb = nbm.blank_fields(text)
            else:
                nb = nbm.blank_fields(text)[1]
            lst.append({'sheet_id': it['sheet_id'], 'content_sha256': it['content_sha256'], 'gold': it['gold'], 'text': text, 'blanked_fields': nb})
        rows[k] = lst
    n_total = sum(len(v) for v in rows.values())
    say(f"repo tree {tree} verified; seals verified for {order}; rows {n_total}; checkpoint {CKPT}; name_blind.py sha256 {sha(blind_src.read_bytes())[:12]}")
    if a.phase == 'dry':
        return 0
    if not resume:
        marker.write_text(json.dumps({'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'variant': a.variant, 'checkpoint': CKPT, 'repo_tree': tree,
                                      'n': {k: len(v) for k, v in rows.items()}, 'system_sha256': sha(system.encode()),
                                      'name_blind_sha256': sha(blind_src.read_bytes()), 'pre_run_note': None}) + '\n')
    else:
        say(f'RESUME {a.phase}: marker present, no final output; sampling only rows missing from {partial.name}')
    from common import load_env_file
    names = load_env_file(Path(__import__("os").environ["TINKER_ENV_FILE"]))
    say(f'env names loaded: {len(names)}; phase={a.phase}')
    import tinker
    service = tinker.ServiceClient()
    client = service.create_sampling_client(model_path=CKPT)
    tok = client.get_tokenizer()
    params = tinker.types.SamplingParams(max_tokens=32, temperature=0, top_p=1, seed=int(lora['seed']))

    def one(item):
        msgs = [{'role': 'system', 'content': system}, {'role': 'user', 'content': item['text']}]
        for att in range(5):
            try:
                t = tr._complete(client, tok, tinker.types, msgs, params)
                return t, tr._as_label(t, labels)
            except Exception:
                if att == 4:
                    raise
                time.sleep(2 * (att + 1))
    allrows = [(k, it) for k in order for it in rows[k]]
    done = {}
    if partial.exists():
        for r in jl(partial):
            done[(r['set'], r['sheet_id'])] = (r['raw'], r['pred'])
    todo = [(k, it) for k, it in allrows if (k, it['sheet_id']) not in done]
    say(f'rows total {len(allrows)}; already sampled {len(done)}; to sample {len(todo)}')
    lock = threading.Lock()
    pf = open(partial, 'a', encoding='utf-8')

    def run(kv):
        k, it = kv
        raw, p = one(it)
        with lock:
            pf.write(json.dumps({'set': k, 'sheet_id': it['sheet_id'], 'raw': raw, 'pred': p}, ensure_ascii=False) + '\n'); pf.flush()
            done[(k, it['sheet_id'])] = (raw, p)
    errors = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for fut in [pool.submit(run, kv) for kv in todo]:
            try:
                fut.result()
            except Exception as e:
                errors.append(type(e).__name__)
    pf.close()
    if errors:
        say(f'WALL: {len(errors)} rows failed after 5 attempts ({sorted(set(errors))}); re-run resumes only the missing rows'); return 4
    preds = {k: [] for k in order}
    for k, it in allrows:
        raw, p = done[(k, it['sheet_id'])]
        preds[k].append({'set': k, 'sheet_id': it['sheet_id'], 'content_sha256': it['content_sha256'], 'gold': it['gold'], 'pred': p, 'raw': raw, 'blanked_fields': it['blanked_fields']})
    tag = 'sealed' if a.phase == 'score' else 'name_blind'
    (OUT / f'{tag}_predictions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for k in order for r in preds[k]), encoding='utf-8')
    views = {k: preds[k] for k in order}
    views['combined'] = [r for k in order for r in preds[k]]
    if a.phase == 'score':
        result = {'variant': a.variant, 'repo_tree': tree, 'checkpoint': CKPT, 'labels': 'configs/router/labels.json (v9, 22)', 'system': 'router.teacher_label.prompt_for(labels)',
                  'parser': 'router.train_router._as_label -> parse_router_output (v9 exact aliases)', 'sampling': {'max_tokens': 32, 'temperature': 0, 'top_p': 1, 'seed': int(lora['seed']), 'enable_thinking': False},
                  'gate': 'evaluate_sealed_gate_v8 (gate v2 + MIN_SEALED_PER_LABEL=%d), unchanged' % MIN_SEALED_PER_LABEL, 'majority_class_fail': mcf,
                  'combined_note': 'combined = the six registered v9 sets concatenated in configs/router/sealed_eval.json order (312 rows); every row sampled once in this run',
                  'precision_note': 'precision = TP / rows predicted as that label (report only; not part of the gate)', 'sets': {}}
        for k, pr in views.items():
            gold = [r['gold'] for r in pr]; pred = [r['pred'] for r in pr]
            g = evaluate_sealed_gate_v8(gold, pred, labels, majority_class_fail=mcf)
            result['sets'][k] = {'n': len(gold), 'accuracy': sum(x == y for x, y in zip(gold, pred)) / len(gold), 'macro_recall': g['gate_v2']['macro_recall'],
                                 'gate_v2_passed': bool(g['gate_v2']['passed']), 'gate_v2': g['gate_v2'], 'router_passed': bool(g['router_passed']), 'per_label': g['per_label'],
                                 'per_label_precision': precision_table(gold, pred, labels),
                                 'pred_counts': dict(Counter(pred)), 'unsure': sum(p == 'unsure' for p in pred),
                                 'confusion_off_diagonal': [[gg, pp, n] for (gg, pp), n in Counter((x, y) for x, y in zip(gold, pred) if x != y).most_common()],
                                 'constant_macro': {lab: macro_recall(gold, [lab] * len(gold), labels) for lab in labels}}
            s = result['sets'][k]
            say(f"{k}: n={s['n']} macro={s['macro_recall']} acc={s['accuracy']:.4f} gate_v2={s['gate_v2_passed']} router_passed={s['router_passed']}")
        (OUT / 'sealed_scores.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    else:
        before = {(r['set'], r['sheet_id']): r['pred'] for r in jl(OUT / 'sealed_predictions.jsonl')}
        res = {'variant': a.variant, 'checkpoint': CKPT, 'repo_tree': tree, 'blanker': 'scripts/router/name_blind.py', 'blanker_sha256': sha(blind_src.read_bytes()), 'sets': {}}
        for k, pr in views.items():
            gold = [r['gold'] for r in pr]; aft = [r['pred'] for r in pr]; bef = [before[(r['set'], r['sheet_id'])] for r in pr]
            table = nbm.flips(gold, bef, aft, labels)
            gate = nbm.name_blind_gate(table, MIN_SEALED_PER_LABEL)
            res['sets'][k] = {'n': len(gold), 'rows_with_blanked_fields': sum(r['blanked_fields'] > 0 for r in pr), 'fields_blanked': sum(r['blanked_fields'] for r in pr),
                              'flips_total': sum(b != x for b, x in zip(bef, aft)),
                              'flips_passable': sum(row['flips'] for row in table.values() if row['n'] >= MIN_SEALED_PER_LABEL),
                              'flips_not_passable': sum(row['flips'] for row in table.values() if row['n'] < MIN_SEALED_PER_LABEL),
                              'flips_on_rows_with_nothing_blanked': sum(r['blanked_fields'] == 0 and r['pred'] != before[(r['set'], r['sheet_id'])] for r in pr),
                              'per_class': table, 'gate': gate,
                              'accuracy_before': sum(x == y for x, y in zip(gold, bef)) / len(gold), 'accuracy_after': sum(x == y for x, y in zip(gold, aft)) / len(gold)}
            s = res['sets'][k]
            say(f"{k} name-blind: flips={s['flips_total']} (passable {s['flips_passable']}, not passable {s['flips_not_passable']}) gate={gate}")
        (OUT / 'name_blind.json').write_text(json.dumps(res, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    try:
        service.close('success').result()
    except Exception:
        pass
    say('DONE ' + a.phase)


if __name__ == '__main__':
    sys.exit(main())
