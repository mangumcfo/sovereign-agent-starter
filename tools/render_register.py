#!/usr/bin/env python3
"""Regenerate BOOK_CODE_OBLIGATION_REGISTER.html's matrix from book_pipeline_status.yaml.

The YAML is canonical; the HTML is a derived view. Edit the YAML, run this, commit both.
Replaces everything between <!-- MATRIX:BEGIN --> and <!-- MATRIX:END --> in the register.
"""
import html
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, '..', 'artifacts')
YAML_PATH = os.path.join(ART, 'book_pipeline_status.yaml')
HTML_PATH = os.path.join(ART, 'BOOK_CODE_OBLIGATION_REGISTER.html')

STEPS = ['outline', 'draft', 'boards', 'figures', 'seeit', 'human_review', 'sealed', 'code', 'published']
MARK = {'done': ('m-done', '✓'), 'in_progress': ('m-prog', '◐'), 'designed_toward': ('m-dt', '◐→'), 'blocked': ('m-block', '✕'),
        'not_started': ('m-ns', '•'), 'not_applicable': ('m-na', '—'), 'unknown': ('m-unk', '?')}


def cell(v):
    cls, sym = MARK.get(v, MARK['unknown'])
    return f'<td class="{cls}">{sym}</td>'


def dlist(items):
    return ''.join(f'<li>{html.escape(i)}</li>' for i in (items or [])) or '<li>—</li>'


def row(rid, label, steps, receipts, bvd, blockers, note_key, series_key='', code_fin=None, hidden=False):
    hcls = ' row-hidden' if hidden else ''
    cells = ''.join(cell(steps.get(s, 'unknown')) for s in STEPS)
    cfin = f'<h4>Code finalization</h4><ul>{dlist(code_fin)}</ul>' if code_fin else ''
    red = any('RED' in (b or '') for b in (blockers or []))
    blk = dlist(blockers)
    if red:
        blk = blk.replace('<li>RED:', '<li class="red">RED:')
    return f'''                <tr class="mrow{hcls}" data-series="{series_key}" onclick="tog('{rid}')"><td>▸ {html.escape(label)}</td>
                    {cells}</tr>
                <tr id="{rid}" class="detail{hcls}" data-series="{series_key}" hidden><td colspan="10"><div class="dgrid">
                    <div class="dcol"><h4>Receipts</h4><ul>{dlist(receipts)}</ul></div>
                    <div class="dcol"><h4>Built vs designed</h4><ul>{dlist(bvd)}</ul>{cfin}</div>
                    <div class="dcol"><h4>Blockers</h4><ul>{blk}</ul>
                    <h4>Notes</h4><textarea class="notes" data-key="{note_key}" placeholder="Your notes…"></textarea></div>
                </div></td></tr>
'''


def rollup_steps(members):
    """Worst-state-wins per step across rollup members (done < unknown < not_started < in_progress < blocked)."""
    order = ['done', 'not_applicable', 'unknown', 'not_started', 'designed_toward', 'in_progress', 'blocked']
    out = {}
    for s in STEPS:
        vals = [m.get('steps', {}).get(s, 'unknown') for m in members]
        out[s] = max(vals, key=lambda v: order.index(v) if v in order else 2)
    return out


def main():
    data = yaml.safe_load(open(YAML_PATH))
    books = data['books']
    rows, rollups = [], {}
    for bid, b in books.items():
        if b.get('is_rollup_meta'):
            rollups.setdefault(b['rollup'], {})['meta'] = b
        elif b.get('rollup'):
            rollups.setdefault(b['rollup'], {}).setdefault('members', []).append(b)
        else:
            label = b['title'] if str(b.get('series')) == 'x' else f"S{b['series']}-V{b['volume']} — {b['title']}"
            rows.append((bid, label, b))
    body = ''
    emitted_rollups = set()
    ordered = []
    for bid, b in books.items():
        if b.get('is_rollup_meta'):
            continue
        g = b.get('rollup')
        if g:
            if g not in emitted_rollups:
                emitted_rollups.add(g)
                ordered.append(('rollup', g))
        else:
            ordered.append(('book', bid))
    def series_key_of(b):
        return 'x' if str(b.get('series')) == 'x' else 's' + str(b.get('series'))

    # per-series aggregate for the bird's-eye summary
    smeta = data.get('series_meta', {})
    agg = {}
    for bid, b in books.items():
        if b.get('is_rollup_meta'):
            continue
        sk = series_key_of(b)
        vals = [v for v in b.get('steps', {}).values() if v != 'not_applicable']
        agg.setdefault(sk, []).extend(vals or ['not_applicable'])
    sumrows, closed_line, closed_series = '', '', set()
    for sk in sorted(agg, key=lambda k: (k == 'x', k)):
        vals = agg[sk]
        m = smeta.get(sk, {})
        if all(v == 'done' for v in vals):
            # SERIES CLOSED (the operator open-holes rule): summarize to one muted line; matrix rows hidden by default
            closed_series.add(sk)
            closed_line += (f'<a href="#" onclick="togSeries(\'{sk}\');return false">{html.escape(m.get("name", sk))}</a> ✓&nbsp;&nbsp;')
            continue
        if all(v in ('not_started', 'unknown', 'not_applicable') for v in vals):
            status, scls = 'Not Started', 'm-ns'
        elif any(v == 'blocked' for v in vals):
            status, scls = 'Partial — RED open', 'm-block'
        else:
            status, scls = 'Partial', 'm-prog'
        sumrows += (f'<tr><td><a href="#" onclick="togSeries(\'{sk}\');return false">{html.escape(m.get("name", sk))}</a></td>'
                    f'<td class="{scls}">{status}</td><td style="text-align:left">{html.escape(m.get("regression", "—"))}</td></tr>\n')
    if closed_line:
        sumrows += (f'<tr><td colspan="3" style="text-align:left" class="m-ns"><em>Closed series (collapsed in the '
                    f'matrix — click a name to show): {closed_line}</em></td></tr>\n')
    summary_html = f'''
        <details class="series-summary">
        <summary><strong>Series summary — bird's-eye. OPEN series show every volume until the whole series closes; closed series collapse (click to expand; series names toggle their matrix rows)</strong></summary>
        <div class="tablewrap"><table>
          <thead><tr><th>Series</th><th>Status</th><th>Regression status</th></tr></thead>
          <tbody>{sumrows}</tbody>
        </table></div>
        </details>'''

    for kind, key in ordered:
        if kind == 'rollup':
            meta = rollups[key].get('meta', {})
            members = rollups[key].get('members', [])
            skey = series_key_of(members[0]) if members else key
            body += row('d-' + key, meta.get('rollup_label', key), rollup_steps(members),
                        meta.get('receipts'), meta.get('built_vs_designed'), meta.get('blockers'), key,
                        skey, None, skey in closed_series)
        else:
            b = books[key]
            label = b['title'] if str(b.get('series')) == 'x' else f"S{b['series']}-V{b['volume']} — {b['title']}"
            body += row('d-' + key, label, b.get('steps', {}),
                        b.get('receipts'), b.get('built_vs_designed'), b.get('blockers'), key,
                        series_key_of(b), b.get('code_finalization'), series_key_of(b) in closed_series)
    src = open(HTML_PATH).read()
    sb, se = '<!-- SUMMARY:BEGIN -->', '<!-- SUMMARY:END -->'
    if sb in src and se in src:
        src = src[:src.index(sb) + len(sb)] + summary_html + '\n        ' + src[src.index(se):]
    begin, end = '<!-- MATRIX:BEGIN -->', '<!-- MATRIX:END -->'
    if begin not in src or end not in src:
        sys.exit('markers not found in register HTML')
    pre = src[:src.index(begin) + len(begin)]
    post = src[src.index(end):]
    stamp = f'\n            <tbody><!-- generated from book_pipeline_status.yaml v{data["meta"]["version"]} ({data["meta"]["date"]}) — edit the YAML, not these rows -->\n'
    open(HTML_PATH, 'w').write(pre + stamp + body + '            </tbody>\n            ' + post)
    print(f'rendered {len(ordered)} rows from {len([b for b in books.values() if not b.get("is_rollup_meta")])} books')


if __name__ == '__main__':
    main()
