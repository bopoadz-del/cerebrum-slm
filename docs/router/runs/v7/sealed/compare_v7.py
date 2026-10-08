"""v6 -> v7-series per-class table on the 312 combined sealed rows, and the owner's promotion criteria (2026-10-08 20:09 +04).

v6 numbers: docs/router/runs/v6/web_f/combined_scores.json (the recorded 312-row aggregation) and the recorded name-blind files.
Variant numbers: this run's sealed_scores.json / name_blind.json. Nothing is re-sampled here.

Precision rule for "no class precision < 0.5": every label that is predicted at least once or present in gold on the 312 rows is
checked. precision = TP / rows predicted as that label. A label present in gold but never predicted counts as precision 0 (fails).
'unsure' is not a label and is not checked.
"""
import json, sys
from pathlib import Path
V6 = Path(sys.argv[1]); OUTDIR = Path(sys.argv[2]); variant = sys.argv[3]
v6c = json.loads((V6 / 'web_f/combined_scores.json').read_text())
v6nb_sets = json.loads((V6 / 'sealed/name_blind.json').read_text())['sets']
v6nb_webf = json.loads((V6 / 'web_f/name_blind.json').read_text())['sets']['web_f_addendum']
v6nb_comb = json.loads((V6 / 'web_f/combined_name_blind.json').read_text())
sc = json.loads((OUTDIR / 'sealed_scores.json').read_text())
nb = json.loads((OUTDIR / 'name_blind.json').read_text())
comb = sc['sets']['combined']
v6pl = {r['label']: r for r in v6c['per_label']}
prec = comb['per_label_precision']
labels = list(v6pl)
rows = []
for lab in labels:
    a, b = v6pl[lab], prec[lab]
    rows.append({'label': lab, 'n': b['n'], 'v6_recall': a['recall'], 'v6_precision': a.get('precision'), 'v6_predicted': a['predicted'],
                 'v7_recall': b['recall'], 'v7_precision': b['precision'], 'v7_predicted': b['predicted'], 'v7_tp': b['tp']})
def P(lab): return prec[lab]['precision']
checked = [lab for lab in labels if prec[lab]['predicted'] > 0 or prec[lab]['n'] > 0]
low = {lab: (P(lab) if P(lab) is not None else 0.0) for lab in checked if (P(lab) if P(lab) is not None else 0.0) < 0.5}
vo = prec['VO/CO']
crit = [
    {'criterion': 'correspondence recall >= 0.5', 'value': prec['correspondence']['recall'], 'pass': prec['correspondence']['recall'] >= 0.5},
    {'criterion': 'payment certificate recall >= 0.75', 'value': prec['payment certificate']['recall'], 'pass': prec['payment certificate']['recall'] >= 0.75},
    {'criterion': 'no class precision < 0.5 (labels predicted or present; never-predicted present label = 0)', 'value': low, 'pass': not low},
    {'criterion': 'VO/CO >= 15/16', 'value': f"{vo['tp']}/{vo['n']}", 'pass': vo['n'] == 16 and vo['tp'] >= 15},
    {'criterion': 'change request precision >= 0.75', 'value': P('change request'), 'pass': (P('change request') or 0.0) >= 0.75},
]
nb_rows = {}
v6_flips = {k: v['flips_total'] for k, v in v6nb_sets.items() if k != 'combined'}
v6_flips['web_f_addendum'] = v6nb_webf['flips_total']; v6_flips['combined'] = v6nb_comb['flips_total']
for k, v in nb['sets'].items():
    nb_rows[k] = {'v6_flips': v6_flips.get(k), 'flips': v['flips_total'], 'flips_passable': v['flips_passable'], 'gate_passed': v['gate']['passed'],
                  'failing_passable_classes': v['gate'].get('failing_passable_classes', [])}
res = {'variant': variant, 'precision_rule': __doc__.split('Precision rule')[1].strip(), 'v6': {'n': v6c['n'], 'macro_recall': v6c['macro_recall'], 'accuracy': v6c['accuracy']},
       'variant_combined': {'n': comb['n'], 'macro_recall': comb['macro_recall'], 'accuracy': comb['accuracy'], 'gate_v2_passed': comb['gate_v2_passed'], 'router_passed': comb['router_passed']},
       'per_set': {k: {'n': v['n'], 'macro_recall': v['macro_recall'], 'accuracy': v['accuracy']} for k, v in sc['sets'].items()},
       'per_class': rows, 'acceptance': crit, 'promoted': all(c['pass'] for c in crit), 'name_blind': nb_rows}
(OUTDIR / f'compare_v6_{variant}.json').write_text(json.dumps(res, indent=2) + '\n')
f = lambda x: '—' if x is None else f'{x:.3f}'
md = [f'| class | n | v6 recall | {variant} recall | v6 precision | {variant} precision |', '|---|---|---|---|---|---|']
for r in rows:
    md.append(f"| {r['label']} | {r['n']} | {f(r['v6_recall'])} | {f(r['v7_recall'])} | {f(r['v6_precision'])} | {f(r['v7_precision'])} |")
print('\n'.join(md))
print(f"macro v6 {v6c['macro_recall']:.4f} -> {comb['macro_recall']:.4f}; acc v6 {v6c['accuracy']:.4f} -> {comb['accuracy']:.4f}")
for c in crit: print(('PASS' if c['pass'] else 'FAIL'), c['criterion'], c['value'])
print('promoted', res['promoted'])
for k, v in nb_rows.items(): print('name-blind', k, v)
