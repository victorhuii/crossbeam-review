"""Only fictional documents and response records are generated here."""
import io
from pathlib import Path

def plan_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    out=io.BytesIO();c=canvas.Canvas(out,pagesize=A4)
    c.setTitle('Fictional demo ADU plans')
    def header(title):
        c.setFont('Helvetica-Bold',20);c.drawString(50,780,title);c.setFont('Helvetica',10);c.drawString(50,758,'FICTIONAL DEMO ONLY - NOT CONSTRUCTION DOCUMENTS')
    header('G-001 / General and site notes')
    c.setFont('Helvetica',12)
    for n,line in enumerate(['Project: Fictional demo ADU','Designer signature: not provided in this fictional sample.','Site plan drainage route: preliminary; civil reviewer to confirm.','All dimensions and notes are illustrative, not legal requirements.']):c.drawString(50,710-n*25,line)
    c.rect(65,330,450,180);c.rect(235,370,170,85);c.setFont('Helvetica',10);c.drawString(250,405,'Illustrative ADU outline');c.drawString(80,480,'Site sketch - not to scale');c.showPage()
    header('A-201 / Elevation study');c.setFont('Helvetica',12)
    c.drawString(50,710,'Proposed roof height is 12 feet in this fictional example.')
    c.drawString(50,685,'The height note is a design statement, not a code limit.')
    c.line(130,370,440,370);c.line(130,370,130,490);c.line(440,370,440,490);c.line(130,490,285,560);c.line(285,560,440,490);c.line(105,370,105,560);c.setFont('Helvetica',10);c.drawString(60,570,'12 ft (fictional)');c.save();return out.getvalue()

def letter_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    out=io.BytesIO();c=canvas.Canvas(out,pagesize=A4);c.setTitle('Fictional corrections letter')
    c.setFont('Helvetica-Bold',20);c.drawString(50,780,'Fictional correction letter');c.setFont('Helvetica',10);c.drawString(50,755,'DEMO ONLY - NOT FROM A REAL CITY OR BUILDING DEPARTMENT')
    c.setFont('Helvetica',12)
    for y,line in [(700,'1. Show the proposed roof height on the elevation sheet.'),(650,'2. Add the designer signature to the title sheet.'),(600,'3. Clarify the drainage route on the site plan.')]:c.drawString(50,y,line)
    c.save();return out.getvalue()

def seed(store):
    existing=next((p for p in store.projects() if p.get('demo')),None)
    if existing:return existing
    p=store.create(dict(name='Fictional demo ADU',jurisdiction='Fictional demo city',adu_type='detached',area_sqft=640),demo=True)
    plans=store.upload(p['id'],'fictional-plans.pdf','plans',raw=plan_pdf());store.upload(p['id'],'fictional-corrections.pdf','letter',raw=letter_pdf())
    items=store.state(p['id'])['items'];first=items[0]
    first=store.evidence(p['id'],dict(item_id=first['id'],revision=first['revision'],document_id=plans['id'],page=2,quote='Proposed roof height is 12 feet in this fictional example.',checked=False))
    store.update_item(p['id'],dict(id=first['id'],revision=first['revision'],status='draft',response='A-201 contains a proposed roof height note. A qualified reviewer must inspect the current drawing and verify applicability before submission.',question=''))
    second=items[1];store.update_item(p['id'],dict(id=second['id'],revision=second['revision'],status='needs_info',response='',question='Who will provide and verify the missing designer signature?'))
    return p

def main():
    from local_review.store import Store
    from local_review.export import pdf,markdown
    import json,tempfile
    root=Path(__file__).resolve().parent/'examples';root.mkdir(exist_ok=True)
    (root/'fictional-plans.pdf').write_bytes(plan_pdf());(root/'fictional-corrections.pdf').write_bytes(letter_pdf())
    with tempfile.TemporaryDirectory() as d:
        store=Store(Path(d)/'demo.db');p=seed(store);state=store.state(p['id'])
        (root/'fictional-response-draft.pdf').write_bytes(pdf(state));(root/'fictional-response-draft.md').write_text(markdown(state));(root/'demo-state.json').write_text(json.dumps(state,indent=2)+'\n')
    print(root)
if __name__=='__main__':main()
