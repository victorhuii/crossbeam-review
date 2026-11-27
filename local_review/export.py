"""Draft-only response packages from explicit reviewer records."""
import io
import re
from html import escape
from pathlib import Path
from local_review.store import now

NOTICE='DRAFT - FOR PROFESSIONAL REVIEW. This package is not a permit approval, code-compliance finding, engineering certification, or legal opinion.'

def md(value):
    value=str(value).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return re.sub(r'([\\`*_{}\[\]()#+!|])',r'\\\1',value)

def markdown(state):
    p=state['project'];docs={d['id']:d for d in state['documents']}
    rows=['# CrossBeam response draft','',NOTICE,'',f"Project: {md(p['name'])}",f"Jurisdiction: {md(p['jurisdiction'])}",f"Declared category / area: {md(p['adu_type'])} / {p['area_sqft']} sq ft",f'Generated: {now()}','',f"Workflow checks open: {len(state['blockers'])}. This is a local checklist state, not a compliance result.",'']
    for item in state['items']:
        origin=docs.get(item['source_document']);where=f"{origin['name']} p. {item['source_page']}" if origin else 'Manually entered correction'
        rows += [f"## Item {md(item['label'])} - {md(item['status'])}",'',f'Correction source: {md(where)}','',md(item['text']),'','Response: '+md(item['response'] or '[Not drafted]'),'']
        if item.get('text_edited') and item.get('original_text'):rows+=['Reviewer-edited correction. Original extracted text: '+md(item['original_text']),'']
        if item['question']:rows+=['Open question: '+md(item['question']),'']
        for e in item['evidence']:
            rows += [f"Evidence: {md(e['document_name'])}, p. {e['page']} / {md(e['source'])} / original checked: {e['checked']}",'', '> '+md(e['quote']).replace('\n','\n> '),'',f"Page SHA-256: {e['page_sha256']}",'']
        if item['reference_url']:rows+=['Reviewer-supplied reference: '+item['reference_url'],'Reference basis: '+md(item['reference_note']),f"Reference applicability checked: {item['reference_checked']}",'']
    rows += ['## Document inspection','']
    for d in state['documents']:
        rows += [f"- {md(d['name'])}: {len(d['pages'])} pages; {d['source']}; inspection recorded: {d['reviewed']}; SHA-256 {d['sha256']}"]
        rows += ['  '+md(w) for w in d['warnings']]
    rows += ['','## Human review checklist','']
    rows += [f"- {md(t['status'])}: {md(t['text'])} Basis: {md(t['note'] or '[Not recorded]')}" for t in state['checklist']]
    rows += ['','## Research entry points','']
    rows += [f"- [{md(s['name'])}]({s['url']}) - link checked {s['checked_at']}. {md(s['scope'])}" for s in state['sources']]
    rows += ['','Source links are research entry points. They were not automatically interpreted or applied to this project.', '', NOTICE, '']
    return '\n'.join(rows)


def pdf(state):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle,getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,KeepTogether
    import reportlab
    fonts=Path(reportlab.__file__).resolve().parent/'fonts'
    for name,file in [('Review','Vera.ttf'),('ReviewBold','VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    glyphs=pdfmetrics.getFont('Review').face.charWidths
    def display(value):return ''.join(c if ord(c) in glyphs or c in '\n\t' else f'[U+{ord(c):04X}]' for c in str(value))
    styles=getSampleStyleSheet()
    body=ParagraphStyle('ReviewBody',fontName='Review',fontSize=9,leading=14,spaceAfter=9,textColor=colors.HexColor('#26353a'),wordWrap='CJK')
    title=ParagraphStyle('ReviewTitle',parent=body,fontName='ReviewBold',fontSize=23,leading=29,spaceAfter=15)
    heading=ParagraphStyle('ReviewHeading',parent=body,fontName='ReviewBold',fontSize=13,leading=18,spaceBefore=16,spaceAfter=10,keepWithNext=True)
    small=ParagraphStyle('ReviewSmall',parent=body,fontSize=8,leading=12,textColor=colors.HexColor('#62747a'))
    def para(value,style=body):return Paragraph(escape(display(value)).replace('\n','<br/>'),style)
    p=state['project'];story=[para('Response review draft',title),para(NOTICE,small),Spacer(1,10),para(p['name'],heading),para(f"Jurisdiction: {p['jurisdiction']}\nDeclared category: {p['adu_type']} / declared area: {p['area_sqft']} sq ft"),para('Generated '+now(),small),para(f"{len(state['blockers'])} workflow checks remain open. Local completion is not an approval or compliance result.")]
    if any(ord(c) not in glyphs and c not in '\n\t' for c in str(state)):story.append(para('Characters outside the embedded font are shown as [U+code]. Use Markdown/JSON for the original Unicode text.',small))
    docs={d['id']:d for d in state['documents']}
    for item in state['items']:
        origin=docs.get(item['source_document']);where=f"{origin['name']} / p. {item['source_page']}" if origin else 'Manually entered correction'
        story += [para(f"Item {item['label']} - {item['status']}",heading),para('Correction source: '+where,small),para(item['text']),para('Response: '+(item['response'] or '[Not drafted]'))]
        if item.get('text_edited') and item.get('original_text'):story.append(para('Reviewer-edited correction. Original extracted text: '+item['original_text'],small))
        if item['question']:story.append(para('Open question: '+item['question']))
        for e in item['evidence']:
            story += [para(f"Evidence: {e['document_name']} / p. {e['page']} / {e['source']} / original checked: {e['checked']}",small),para('Quote: '+e['quote']),para('Page SHA-256: '+e['page_sha256'],small)]
        if item['reference_url']:story += [para('Reviewer reference: '+item['reference_url'],small),para(f"Applicability checked: {item['reference_checked']}. Basis: {item['reference_note']}",small)]
    story.append(para('Document inspection',heading))
    for d in state['documents']:
        story += [para(f"{d['name']} / {len(d['pages'])} pages / {d['source']} / original inspection recorded: {d['reviewed']}"),para('SHA-256: '+d['sha256'],small)]
        story += [para(w,small) for w in d['warnings']]
    story.append(para('Human review checklist',heading))
    for task in state['checklist']:story += [para(task['status'].upper()+' - '+task['text']),para('Review basis: '+(task['note'] or '[Not recorded]'),small)]
    story.append(para('Research entry points',heading))
    for source in state['sources']:story += [para(source['name']),para(source['url'],small),para(f"Link checked {source['checked_at']}. {source['scope']}",small)]
    story.append(para('Research links are entry points only. Verify current law and jurisdiction applicability independently.',small))
    output=io.BytesIO();doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=46,leftMargin=46,topMargin=46,bottomMargin=48,title='CrossBeam response draft',author='CrossBeam Review local workspace')
    def footer(canvas,document):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d9e3e5'));canvas.line(46,37,A4[0]-46,37);canvas.setFont('Review',7);canvas.setFillColor(colors.HexColor('#62747a'));canvas.drawString(46,24,'DRAFT - FOR PROFESSIONAL REVIEW');canvas.drawRightString(A4[0]-46,24,f'Page {document.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
