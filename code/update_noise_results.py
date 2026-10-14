#!/usr/bin/env python3
"""Generate added tables/plots from the exact frozen imperfect-detector sweep."""
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / 'extensions/noisy_audit'


def exact(row, field):
    return Fraction(row[field + '_exact'])


def percentage(value):
    if value == 0:
        return '0.00'
    if value < Fraction(1, 100000000):
        return r'$<10^{-6}$'
    return f'{float(value) * 100:.2f}'


def build():
    source = EXT / 'results_primary/results.csv'
    rows = list(csv.DictReader(source.open()))
    assert len(rows) == 3250
    summary = json.loads((EXT / 'results_primary/summary.json').read_text())

    def get(policy, q, n, K):
        matches = [r for r in rows if r['policy'] == policy and r['actual_q'] == q
                   and int(r['n']) == n and int(r['K']) == K]
        assert len(matches) == 1
        return matches[0]

    selected = [
        ('Perfect detector', get('calibrated_independent', '1', 64, 64)),
        ('Naive perfect-test bound', get('naive_perfect_detector', '9/10', 64, 64)),
        ('Known independent sensitivity', get('calibrated_independent', '9/10', 64, 64)),
        ('Known independent sensitivity', get('calibrated_independent', '9/10', 64, 34)),
        ('Overstated sensitivity', get('misspecified_sensitivity', '7/10', 64, 34)),
        ('Shared detector blind spot', get('correlation_violation', '9/10', 64, 64)),
    ]
    lines = [r'\subsection{Exact operating characteristics}',
             'The complete sweep sums 68,984 feasible observed-count outcomes. Across all 1,300 correctly specified independent scenarios, neither bound undercoverage nor unsafe certification exceeds 0.05. The maximum undercoverage is 0.0499842; maximum unsafe certification is 0.0481443. These are maxima over the declared finite grid, not measured workload failure frequencies or a claim about every detector model.',
             r'\begin{table}[ht]\centering\small',
             r'\begin{tabular}{lrrrrr}\toprule',
             r'Scenario & $K$ & $q$ & $q_0$ & Certify (\%) & Unsafe (\%)\\\midrule']
    for name, row in selected:
        q = f"{float(Fraction(row['actual_q'])):g}"
        q0 = f"{float(Fraction(row['assumed_q0'])):g}"
        lines.append(f"{name} & {row['K']} & {q} & {q0} & "
                     f"{percentage(exact(row, 'pass_probability'))} & "
                     f"{percentage(exact(row, 'unsafe_pass_probability'))} " + r'\\')
    lines += [r'\bottomrule\end{tabular}',
              r'\caption{Selected fixed scenarios, all with $N=n=64$ and residual tolerance six. Unsafe means certification with more than six stale claims, unconditionally over detector randomness. The shared-blind-spot row violates independence; the overstated-sensitivity row violates $q\ge q_0$. Tiny nonzero probabilities are shown as an upper display threshold, not rounded to zero.}\label{tab:noisy}',
              r'\end{table}',
              'With an imperfect detector, a census is not exact settlement. For the naive perfect-test bound at $n=N$, $U(Y)=Y$, so its residual bound is always zero and every outcome passes. With actual independent sensitivity 0.9 and $K=64$, the chance of leaving more than six stale claims is 0.4609612. With actual sensitivity 0.5, it is greater than 0.99999999999. These are controlled counterexamples to transferring the perfect-validator interpretation, not empirical model measurements.',
              'Correct specification has an availability cost. At sample size 16, no correctly specified case in this sensitivity grid can certify the six-claim tolerance, even when $K=0$. At sample size 24, sensitivities 0.7 and 0.5 also permit no certification at any observed count. Withholding is reported as withholding, not as successful repair.',
              r'The unconditional denominator matters. In the correctly specified $n=64,K=34,q=0.9$ scenario, both certification and unsafe certification have probability 0.0481443. Thus all certified outcomes in this particular scenario are unsafe, despite satisfying the unconditional 0.05 control. This explicitly disproves interpreting the bound as 95\% correctness among passed audits.',
              'Overstating sensitivity can be much worse: at $n=64,K=34$, actual sensitivity 0.7 with assumed lower bound 0.9 yields unsafe certification probability 0.9214717. A shared all-or-none detector with marginal sensitivity 0.9 yields unsafe probability 0.1 at $K=64,n=64$. These intentionally violate calibration or independence. They do not refute the conditional assumptions of the exact bound. All result files in a complete replay are byte-identical; ten additional implementation tests pass.',
              r'\begin{figure}[!htbp]\centering']
    plot_specs = [('calibrated_independent', '9/10', 'blue!70!black', 'solid', 'Known independent sensitivity'),
                  ('naive_perfect_detector', '9/10', 'red!70!black', 'dashed', 'Naive perfect-test bound'),
                  ('correlation_violation', '9/10', 'violet', 'densely dotted', 'Shared blind spot (assumption violated)')]
    plotted = []
    for field, ylabel in [('unsafe_pass_probability', 'Unsafe certification (\\%)'),
                          ('pass_probability', 'Certification (\\%)')]:
        lines += [r'\begin{tikzpicture}\begin{axis}[width=0.93\linewidth,height=5.1cm,'
                  + f'xlabel={{True stale count before audit $K$}},ylabel={{{ylabel}}},'
                  + r'xmin=0,xmax=64,xtick={0,8,16,24,32,40,48,56,64},ymin=0,ymax=104,grid=major,legend style={font=\scriptsize,at={(0.5,-0.26)},anchor=north,legend columns=1},label style={font=\small},tick label style={font=\small}]']
        if field.startswith('unsafe'):
            lines.append(r'\addplot[color=gray,dashed,forget plot] coordinates {(0,5) (64,5)};')
        for policy, q, color, style, label in plot_specs:
            series = sorted([r for r in rows if r['policy'] == policy and r['actual_q'] == q and r['n'] == '64'], key=lambda r: int(r['K']))
            points = [(int(r['K']), 100 * float(exact(r, field))) for r in series]
            coords = ' '.join(f'({x},{y:.9f})' for x, y in points)
            lines += [f'\\addplot[color={color},{style},thick] coordinates {{{coords}}};',
                      f'\\addlegendentry{{{label}}}']
            plotted.append({'field': field, 'policy': policy, 'actual_q': q, 'n': 64, 'points_percent': points})
        lines += [r'\end{axis}\end{tikzpicture}', r'\vspace{1.4cm}']
    lines += [r'\caption{Exact fixed-population operating characteristics with a full 64-claim audit, marginal sensitivity 0.9 and residual tolerance six. Top: unconditional unsafe certification. Bottom: certification probability, exposing withholding. Independent known-sensitivity correction and naive perfect-test interpretation use the same actual independent detector. The shared-blind-spot curve uses a different correlated detector with the same marginal sensitivity, intentionally violating the correction assumptions. These curves are probability-model calculations, not observed Manor model behavior.}\label{fig:noisy}',
              r'\end{figure}\FloatBarrier']
    manuscript = ROOT / 'Manor_AI_Paper_2.tex'
    text = manuscript.read_text()
    begin, end = '% BEGIN_NOISY_RESULTS', '% END_NOISY_RESULTS'
    assert text.count(begin) == text.count(end) == 1
    prefix, rest = text.split(begin)
    _, suffix = rest.split(end)
    manuscript.write_text(prefix + begin + '\n' + '\n\n'.join(lines) + '\n' + end + suffix)
    figure_dir = ROOT / 'figures'
    data = {'source_csv_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'probabilities_computed_exactly_displayed_as_floats': True, 'series': plotted,
            'selected_table_rows': [{'label': label, **row} for label, row in selected]}
    (figure_dir / 'noisy_plot_data.json').write_text(json.dumps(data, indent=2) + '\n')
    import matplotlib
    matplotlib.use('Agg')
    matplotlib.rcParams['svg.hashsalt'] = 'workspace-repair-audit-v0.1.1'
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(9, 9), sharex=True, constrained_layout=True)
    colors = ['#185aa0', '#c63d30', '#8652a0']
    styles = ['-', '--', ':']
    for ax, field in zip(axes, ['unsafe_pass_probability', 'pass_probability']):
        for item, color, style, spec in zip([p for p in plotted if p['field'] == field], colors, styles, plot_specs):
            ax.plot(*zip(*item['points_percent']), color=color, linestyle=style, linewidth=2, label=spec[-1])
        ax.set(ylabel=('Unsafe certification (%)' if field.startswith('unsafe') else 'Certification (%)'), ylim=(-1, 103), xlim=(0, 64))
        ax.grid(alpha=.2)
        ax.legend(fontsize=9, loc='best')
    axes[0].axhline(5, color='#777777', linewidth=.8)
    axes[1].set_xlabel('True stale claims before audit K')
    fig.suptitle('Exact detector-noise audit: N = n = 64, marginal sensitivity = 0.9', fontsize=12)
    fig.savefig(figure_dir / 'noisy_audit.png', dpi=180)
    fig.savefig(figure_dir / 'noisy_audit.svg', metadata={'Date': None})
    plt.close(fig)
    print(json.dumps({'rows': len(rows), 'feasible_outcomes': summary['exact_feasible_y_outcomes_summed'], 'figure': 'figures/noisy_audit.png'}))


if __name__ == '__main__':
    build()
