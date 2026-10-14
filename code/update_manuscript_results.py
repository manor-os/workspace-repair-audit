"""Insert tables and standalone pgfplots coordinates from measured results."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
PAPER=ROOT/'Manor_AI_Paper_2.tex'
LABELS={'observed_closure':'Observed closure (diagnostic)','closure_priority_36':'Closure priority, 36',
        'lexical_36':'Lexical, 36','uniform_36':'Uniform, 36','risk_36':'Public signals, 36',
        'hybrid_36':'Ranked + uniform, 36','ranked_audit_gate':'Audit + fallback','full_scan':'Full inspection (diagnostic)'}
METHODS=list(LABELS)
COLORS={'observed_closure':'gray','closure_priority_36':'orange','lexical_36':'magenta',
        'uniform_36':'red!70!black','risk_36':'blue!70!black','hybrid_36':'violet',
        'ranked_audit_gate':'green!45!black','full_scan':'black'}

def main():
    s=json.loads((ROOT/'results_primary/summary.json').read_text())['methods']
    plot=json.loads((ROOT/'figures/plot_data.json').read_text())
    assert plot['gate']=={'passes':253,'fallbacks':1187,'passed_all_current':119,
                         'passed_with_residual':134,'unsafe_releases':6,'coverage_failures':34}
    rows=[]
    for m in METHODS:
        r=s[m]
        rows.append(f"{LABELS[m]} & {r['mean_validations']:.2f} & {r['mean_residual_stale']:.2f} & {r['all_current_instances']}/1440 \\\\")
    table='\n'.join(rows)
    text=r'''\subsection{Matched budgets and observed provenance}
Table~\ref{tab:results} reports all eight policies on the 1,440 paired workspace-condition instances. The 36-call public-signal ranking leaves fewer stale claims on average than the other fixed-budget policies in this generator. The 12-ranked/24-uniform hybrid is worse than using all 36 calls for public-signal ranking. Thus random audit allocation has a measurable discovery opportunity cost here; adding random checks does not automatically improve fixed-budget repair.

\begin{table}[ht]
\centering\small
\begin{tabular}{lrrr}
\toprule
Policy & Mean calls & Mean residual & All current\\\midrule
''' + table + r'''
\bottomrule
\end{tabular}
\caption{Measured results, 64 claims per instance. Five policies have exactly 36 calls. Full inspection is an idealized exact-validator diagnostic. Four conditions share each of 360 base workspaces; no population inference is made.}\label{tab:results}
\end{table}

Observed closure becomes cheaper as missing edges hide more descendants, while leaving more stale claims. This is a failure mode of using graph-induced cost reduction as evidence of successful repair. The complete observed-true-edge condition reaches all actual obligations, though incorrect edges can cause unnecessary checks. Conditions with missing edges progressively undermine this coverage.

\subsection{The cost and failures of the audit gate}
The audit policy passes after 36 calls in 253 instances and falls back to all 64 calls in 1,187. Its mean of 59.08 calls saves 7.69\% relative to full inspection in this cost model. It leaves no stale claims in 1,306/1,440 instances (90.69\%), compared with 1,440/1,440 for idealized full inspection. This difference is not a like-for-like correctness improvement: the audit policy explicitly permits up to six residual claims on a successful count-bound event.

Only 119 of the 253 gate-passed instances have every claim current. The other 134 retain at least one stale claim, and six retain more than the allowed six. The six unsafe gate releases are 6/1,440 of all instances and 6/253 of passed instances; these descriptive denominators must not be interchanged. The overall fully-current fraction is dominated by the 1,187 full-inspection fallbacks. Across all planned audits, 34 realized confidence bounds under-cover the actual remaining count. These failures are retained in the raw evidence rather than removed as outliers.

The nominal bound is per fixed instance under uniform sampling, not a promise that every realized audit is correct. It also does not assert 95\% correctness conditional on passing the gate. The deterministic seeded corpus is a collection of fixed realizations, not a Monte Carlo estimate of coverage. The probability argument comes from the sampling model and exact combinatorial enumeration.

\subsection{Exact checks, reproducibility and model feasibility}
The exact small-population sanity check covers 819 $(N,n,K)$ combinations and 1,820 feasible count outcomes for $N\le12$, with maximum undercoverage probability $1/20$. Thirteen offline tests pass. An independent reviewer also enumerated the actual audit design $(N,n)=(52,24)$ across every feasible $K,k$: maximum bound undercoverage is approximately 0.04927 and maximum unsafe-release probability under the six-claim threshold is approximately 0.04189. These checks validate the known bound's implementation under ideal labels, not semantic inspection quality.

A complete held-out rerun produces byte-identical detailed traces, CSV results, summaries and manifests. It adds no independent workspaces. The existing local Manor owner's selected model route was checked as BYOK. Two bounded synthetic routing smoke attempts did not yield a successful completion; the recorded diagnostic retry returned a BYOK provider HTTP 502 error. They are feasibility failures, not benchmark cases or model-performance observations. The main experiment has zero language-model calls and must be read as a routing/auditing prototype.
'''
    figure_methods=['observed_closure','closure_priority_36','uniform_36','risk_36','hybrid_36','ranked_audit_gate','full_scan']
    text+=r'''
\begin{figure}[htbp]
\centering
'''
    for metric,ylabel,ymax in [('mean_residual','Remaining stale claims',16),('mean_calls','Validation calls',68)]:
        text+=r'\begin{tikzpicture}\begin{axis}[width=0.94\linewidth,height=5.1cm,xlabel={True-edge deletion probability (\%)},ylabel={'+ylabel+'},xmin=0,xmax=50,ymin=0,ymax='+str(ymax)+r',xtick={0,10,30,50},grid=major,legend style={font=\scriptsize,at={(0.5,-0.27)},anchor=north,legend columns=2},label style={font=\small},tick label style={font=\small}]'+'\n'
        for m in figure_methods:
            coords=' '.join(f"({r['missing_rate']*100:g},{r[metric]:.6f})" for r in plot['curves'][m])
            text+=f"\\addplot[color={COLORS[m]},mark=*,mark size=1.4pt] coordinates {{{coords}}};\n"
            text+=f"\\addlegendentry{{{LABELS[m].replace('(diagnostic)','').strip()}}}\n"
        text+=r'\end{axis}\end{tikzpicture}'+'\n\n'+r'\vspace{1.2cm}'+'\n'
    text+=r'''\caption{Measured residual claims and validation calls across missing-edge conditions; each point averages 360 generated base workspaces. Declining closure cost coincides with worse coverage. The audited policy includes its fallback cost. These are validator-call counts, not token or monetary savings.}\label{fig:missing}
\end{figure}

\begin{figure}[ht]
\centering
\begin{tikzpicture}\begin{axis}[width=0.94\linewidth,height=5cm,xlabel={Mean charged validation calls},ylabel={All claims current (\%)},xmin=31,xmax=68,ymin=0,ymax=106,grid=major,label style={font=\small},tick label style={font=\small}]
'''
    for m in ['uniform_36','risk_36','ranked_audit_gate','full_scan']:
        r=s[m];x=r['mean_validations'];y=100*r['all_current_instance_fraction']
        text+=f"\\addplot[only marks,color={COLORS[m]},mark=*,mark size=2pt] coordinates {{({x:.6f},{y:.6f})}};\n"
        pos='above right' if m in ['uniform_36','risk_36'] else 'below left'
        label=LABELS[m].replace(' (diagnostic)','')
        text+=f"\\node[{pos},font=\\scriptsize] at (axis cs:{x:.6f},{y:.6f}) {{{label}}};\n"
    text+=r'''\end{axis}\end{tikzpicture}
\caption{Selected policies illustrate the cost/correctness tradeoff. Audit plus fallback saves only 7.69\% of validation calls and has lower all-current frequency than full inspection. Its release tolerance explicitly allows nonzero residuals.}\label{fig:cost}
\end{figure}
\FloatBarrier
'''
    source=PAPER.read_text()
    start='% BEGIN_AUTOGENERATED_RESULTS';end='% END_AUTOGENERATED_RESULTS'
    if '% RESULT_SECTION' in source:
        source=source.replace('% RESULT_SECTION',start+'\n'+text+'\n'+end)
    else:
        a=source.index(start);b=source.index(end,a)+len(end)
        source=source[:a]+start+'\n'+text+'\n'+end+source[b:]
    PAPER.write_text(source)
    print('Results tables and plot coordinates generated from primary data.')

if __name__=='__main__':main()
