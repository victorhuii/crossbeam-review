"""Generate project graphics from the fictional saved review state."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1];out=root/'docs/assets';out.mkdir(parents=True,exist_ok=True)
state=json.loads((root/'examples/demo-state.json').read_text());bg='#fafcfc';ink='#28373b';muted='#65757b';accent='#32666e'
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','text.color':ink})
def save(fig,name):
 for ext in ['png','svg']:
  p=out/f'{name}.{ext}';fig.savefig(p,dpi=160,facecolor=bg)
  if ext=='svg':p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
 plt.close(fig)
fig=plt.figure(figsize=(8,4),facecolor=bg);fig.text(.065,.85,'PERMIT RESPONSE / LOCAL REVIEW',size=10,color=accent,weight='bold');fig.text(.065,.64,'CrossBeam Review',size=33);fig.text(.065,.50,'Keep corrections, evidence, and review decisions together.',size=13,color=muted);fig.text(.065,.29,'Page citations / Explicit open questions / Draft-only exports',size=12,color=accent);fig.text(.065,.12,'Local extension of CrossBeam by Mike Brown. New workflow by Victor Hui.',size=9.5,color=muted);save(fig,'cover')
fig=plt.figure(figsize=(10,6.25),facecolor=bg);fig.text(.07,.90,'CROSSBEAM REVIEW',size=11,color=accent,weight='bold');fig.text(.07,.80,'Unresolved work stays visible',size=25);fig.text(.07,.73,'Fictional demo state · workflow counts, not permit outcomes',size=12,color=muted)
labels=['To review','Needs information','Draft','Reviewed'];keys=['todo','needs_info','draft','reviewed'];counts=[sum(i['status']==k for i in state['items']) for k in keys]
ax=fig.add_axes([.12,.30,.77,.32],facecolor=bg);ax.bar(labels,counts,color=[accent,'#b2804f','#819da4','#c3d2d6'],width=.5);ax.set_ylim(0,2);ax.set_yticks([0,1,2]);ax.tick_params(length=0,labelsize=12)
for edge in ax.spines.values():edge.set_visible(False)
for n,count in enumerate(counts):ax.text(n,count+.08,str(count),ha='center',size=15)
fig.text(.07,.18,f"{len(state['blockers'])} workflow checks open. One attached quote still needs original-context review.",size=12,color=muted);fig.text(.07,.10,'Source: generated fictional demo-state.json. No compliance or approval result is inferred.',size=10.5,color=muted);save(fig,'review-state')
print('Generated two PNG/SVG pairs')
