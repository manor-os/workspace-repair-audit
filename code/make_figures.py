"""Generate figures and inline LaTeX coordinates from actual frozen-run CSV."""
from __future__ import annotations
import argparse, csv, json, os
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'figures'/'mpl_cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS={'observed_closure':'Observed closure','closure_priority_36':'Closure priority (36)',
        'lexical_36':'Lexical (36)','uniform_36':'Uniform (36)','risk_36':'Public signals (36)',
        'hybrid_36':'Ranked + uniform (36)','ranked_audit_gate':'Audit + fallback','full_scan':'Full inspection'}
COLORS={'observed_closure':'#7c7c7c','closure_priority_36':'#d88926','lexical_36':'#b36a9f',
        'uniform_36':'#a43d3d','risk_36':'#2563a6','hybrid_36':'#6b54a3',
        'ranked_audit_gate':'#18816c','full_scan':'#222222'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=ROOT/'results_primary');a=p.parse_args()
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    rows=list(csv.DictReader((a.results/'results.csv').open()))
    groups=defaultdict(list)
    for r in rows:groups[(r['method'],float(r['missing_edge_rate']))].append(r)
    curves={}
    for method in LABELS:
        curves[method]=[]
        for rate in [0,.1,.3,.5]:
            rs=groups[(method,rate)]
            curves[method].append({'missing_rate':rate,'n':len(rs),
                'mean_residual':sum(float(r['residual_stale_count']) for r in rs)/len(rs),
                'mean_calls':sum(float(r['validator_calls']) for r in rs)/len(rs),
                'all_current_fraction':sum(r['all_claims_current']=='True' for r in rs)/len(rs)})
    gate=[r for r in rows if r['method']=='ranked_audit_gate']
    passed=[r for r in gate if r['certificate_passed']=='True']
    analysis={'distinct_instances':len({r['case_id'] for r in rows}),
        'base_workspaces':len({r['base_id'] for r in rows}),
        'curves':curves,'gate':{'passes':len(passed),'fallbacks':len(gate)-len(passed),
            'passed_all_current':sum(r['all_claims_current']=='True' for r in passed),
            'passed_with_residual':sum(int(r['residual_stale_count'])>0 for r in passed),
            'unsafe_releases':sum(r['unsafe_gate_release']=='True' for r in gate),
            'coverage_failures':sum(r['certificate_coverage_failure']=='True' for r in gate)},
        'interpretation':'Descriptive generated-case averages. Four conditions share each base. No population CI or LLM cost inference.'}
    (out/'plot_data.json').write_text(json.dumps(analysis,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.4),layout='constrained')
    chosen=['observed_closure','closure_priority_36','uniform_36','risk_36','hybrid_36','ranked_audit_gate','full_scan']
    for m in chosen:
        xx=[r['missing_rate']*100 for r in curves[m]]
        axes[0].plot(xx,[r['mean_residual'] for r in curves[m]],label=LABELS[m],color=COLORS[m],marker='o',markersize=4)
        axes[1].plot(xx,[r['mean_calls'] for r in curves[m]],label=LABELS[m],color=COLORS[m],marker='o',markersize=4)
    for ax in axes:
        ax.set_xlabel('True-edge deletion probability (%)');ax.set_xticks([0,10,30,50]);ax.grid(alpha=.18)
    axes[0].set_ylabel('Mean remaining stale claims (of 64)');axes[1].set_ylabel('Mean validation calls (of 64)')
    axes[1].set_ylim(0,68)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=4,frameon=False,fontsize=9)
    fig.savefig(out/'missing_provenance.png',dpi=190);fig.savefig(out/'missing_provenance.svg');plt.close(fig)
    summary=json.loads((a.results/'summary.json').read_text())['methods']
    order=['uniform_36','lexical_36','hybrid_36','closure_priority_36','risk_36','ranked_audit_gate','full_scan']
    fig,ax=plt.subplots(figsize=(9.4,4.6),layout='constrained')
    xx=[summary[m]['mean_validations'] for m in order];yy=[summary[m]['all_current_instance_fraction']*100 for m in order]
    for m,x,y in zip(order,xx,yy):
        ax.scatter(x,y,color=COLORS[m],s=55)
        offsets={'uniform_36':(7,-2),'lexical_36':(7,1),'hybrid_36':(7,8),'closure_priority_36':(7,-9),'risk_36':(7,5),'ranked_audit_gate':(-100,-10),'full_scan':(-92,-3)}
        ax.annotate(LABELS[m],(x,y),xytext=offsets[m],textcoords='offset points',fontsize=9)
    ax.set_xlabel('Mean charged validation calls');ax.set_ylabel('Instances with every claim current (%)')
    ax.set_xlim(31,68);ax.set_ylim(-5,106);ax.grid(alpha=.18)
    fig.savefig(out/'cost_correctness.png',dpi=190);fig.savefig(out/'cost_correctness.svg');plt.close(fig)
    lines=[]
    for m in chosen:
        residual=' '.join(f"({r['missing_rate']*100:g},{r['mean_residual']:.6f})" for r in curves[m])
        calls=' '.join(f"({r['missing_rate']*100:g},{r['mean_calls']:.6f})" for r in curves[m])
        lines += [f'% {m}',f'% residual: {residual}',f'% calls: {calls}']
    (out/'latex_coordinates.txt').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'figures':2,'raw_rows':len(rows),'gate':analysis['gate'],'output':str(out)},indent=2))

if __name__=='__main__':main()
