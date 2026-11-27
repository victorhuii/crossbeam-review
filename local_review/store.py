"""Local evidence records, conservative review gates, and an append-only audit."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import threading
from urllib.parse import urlsplit
from uuid import uuid4

from local_review.documents import label,digest,extract_pdf,text_pages,correction_candidates,match_quote,search_pages

ROOT=Path(__file__).resolve().parent
SOURCES=json.loads((ROOT/'sources.json').read_text())

def now():return datetime.now(timezone.utc).isoformat()
def uid():return str(uuid4())
def text(value,limit):
    if not isinstance(value,str) or len(value)>limit:raise ValueError(f'Text limit is {limit} characters')
    return value.strip()
def safe_url(value):
    value=text(value,1000)
    if not value:return ''
    try:p=urlsplit(value)
    except ValueError:raise ValueError('Invalid source URL')
    if p.scheme!='https' or not p.hostname or p.username or p.password or any(ord(c)<32 for c in value):raise ValueError('Source URL must be HTTPS without credentials')
    return value

def checklist_for(project):
    tasks=[('identity','Confirm project identity, jurisdiction, application category, and current forms.'),('site','Review the site plan, property boundaries, dimensions, access, and applicable setbacks.'),('floor','Review existing/proposed floor plans and declared area.'),('elevation','Review elevations, height information, and drawing consistency.'),('structural','Confirm structural documents and required professional review.'),('systems','Confirm applicable energy, utility, drainage, fire, and accessibility review.'),('signatures','Inspect required signatures, stamps, dates, and drawing revisions visually.'),('process','Confirm the current local submission process and required attachments.')]
    if project['adu_type'] in ('conversion','jadu'):tasks.append(('existing','Confirm existing-condition records and the applicability of conversion/JADU provisions.'))
    return [dict(id=key,text=value,status='pending',note='',revision=0) for key,value in tasks]


def item_blockers(item):
    problems=[]
    if not item['response'].strip():problems.append('Write a response')
    if not item['evidence']:problems.append('Attach page evidence')
    elif not all(e['checked'] for e in item['evidence']):problems.append('Check every attached quote against its original document')
    if item['reference_url'] and not item['reference_checked']:problems.append('Check the cited legal/reference source and applicability')
    if item['reference_url'] and not item['reference_note'].strip():problems.append('Record the cited reference basis and applicability')
    if item['question'].strip():problems.append('Resolve or clear the open question')
    return problems


class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock()
        with self.db() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),payload TEXT NOT NULL,raw BLOB);
            CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checklist(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,project_id TEXT NOT NULL,created TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL);
            ''')
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=10);db.execute('PRAGMA foreign_keys=ON')
            try:yield db;db.commit()
            except Exception:db.rollback();raise
            finally:db.close()
    def _event(self,db,pid,kind,data):db.execute('INSERT INTO events(project_id,created,kind,payload) VALUES(?,?,?,?)',(pid,now(),kind,json.dumps(data)))
    def _get(self,db,table,id,pid=None):
        row=db.execute(f'SELECT payload FROM {table} WHERE id=?'+(' AND project_id=?' if pid else ''),(id,pid) if pid else (id,)).fetchone()
        if not row:raise ValueError('Record not found in this project')
        return json.loads(row[0])
    def projects(self):
        with self.db() as db:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM projects ORDER BY rowid')]
    def create(self,body,demo=False):
        name=label(body.get('name'));jurisdiction=label(body.get('jurisdiction'));adu_type=body.get('adu_type')
        if adu_type not in ('detached','attached','conversion','jadu'):raise ValueError('Select an ADU category')
        size=body.get('area_sqft')
        if isinstance(size,bool) or not isinstance(size,(int,float)) or not 1<=size<=12000:raise ValueError('Declared area must be 1–12000 square feet; this is not an eligibility check')
        project=dict(id=uid(),name=name,jurisdiction=jurisdiction,adu_type=adu_type,area_sqft=size,created_at=now(),demo=demo)
        with self.db() as db:
            if db.execute('SELECT count(*) FROM projects').fetchone()[0]>=10:raise ValueError('Maximum 10 local projects')
            db.execute('INSERT INTO projects VALUES(?,?)',(project['id'],json.dumps(project)))
            for task in checklist_for(project):
                task['id']=project['id']+':'+task['id'];db.execute('INSERT INTO checklist VALUES(?,?,?)',(task['id'],project['id'],json.dumps(task)))
            self._event(db,project['id'],'project_created',project)
        return project
    def upload(self,pid,name,kind,raw=None,content=None):
        name=label(name,120)
        if '/' in name or '\\' in name:raise ValueError('Use a filename, not a path')
        if kind not in ('plans','letter','reference'):raise ValueError('Choose plans, letter, or reference')
        pages,warnings=extract_pdf(raw) if raw is not None else text_pages(content)
        source='pdf_text' if raw is not None else 'manual_text';sha=digest(raw if raw is not None else content.encode())
        doc=dict(id=uid(),name=name,kind=kind,pages=pages,warnings=warnings,source=source,sha256=sha,reviewed=False,created_at=now())
        candidates=correction_candidates(pages) if kind=='letter' else []
        with self.db() as db:
            self._get(db,'projects',pid)
            existing=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents WHERE project_id=?',(pid,))]
            duplicate=next((d for d in existing if d['sha256']==sha and d['kind']==kind),None)
            if duplicate:return duplicate
            if len(existing)>=10:raise ValueError('Maximum 10 documents per project')
            if db.execute('SELECT count(*) FROM items WHERE project_id=?',(pid,)).fetchone()[0]+len(candidates)>100:raise ValueError('Maximum 100 correction items per project')
            db.execute('INSERT INTO documents VALUES(?,?,?,?)',(doc['id'],pid,json.dumps(doc),raw))
            for c in candidates:
                item=dict(id=uid(),label=c['label'],text=c['text'],original_text=c['text'],text_edited=False,source_document=doc['id'],source_page=c['page'],status='todo',response='',question='',reference_url='',reference_note='',reference_checked=False,evidence=[],revision=0)
                db.execute('INSERT INTO items VALUES(?,?,?)',(item['id'],pid,json.dumps(item)))
            self._event(db,pid,'document_imported',dict(id=doc['id'],sha256=sha,source=source,candidate_items=len(candidates)))
        return doc
    def document(self,pid,did):
        with self.db() as db:return self._get(db,'documents',did,pid)
    def raw(self,pid,did):
        with self.db() as db:
            row=db.execute('SELECT raw FROM documents WHERE id=? AND project_id=?',(did,pid)).fetchone()
            if not row or row[0] is None:raise ValueError('No original PDF stored for this record')
            return row[0]
    def page(self,pid,did,number):
        doc=self.document(pid,did)
        if isinstance(number,bool) or not isinstance(number,int) or not 1<=number<=len(doc['pages']):raise ValueError('Page not found')
        return doc['pages'][number-1]
    def _revision(self,item,body):
        if type(body.get('revision')) is not int or body['revision']!=item['revision']:raise ValueError('Record changed in another action; reload before saving')
    def update_item(self,pid,body):
        with self.db() as db:
            item=self._get(db,'items',body.get('id'),pid);self._revision(item,body);before=dict(item)
            working=text(body.get('correction_text',item['text']),3000)
            if not working:raise ValueError('Correction text cannot be empty')
            item.setdefault('original_text',item['text'] if item['source_document'] else None)
            item.update(text=working,text_edited=working!=item['original_text'],label=label(body.get('label',item['label']),30))
            item.update(response=text(body.get('response',''),6000),question=text(body.get('question',''),2000),reference_url=safe_url(body.get('reference_url','')),reference_note=text(body.get('reference_note',''),2000),reference_checked=body.get('reference_checked') is True,status=body.get('status'))
            if item['status'] not in ('todo','needs_info','draft','reviewed'):raise ValueError('Invalid review status')
            if item['status']=='needs_info' and not item['question']:raise ValueError('Describe the missing information')
            if item['status']=='reviewed':
                blockers=item_blockers(item)
                if blockers:raise ValueError('; '.join(blockers))
                if body.get('confirm_review') is not True:raise ValueError('Explicitly confirm human review before marking reviewed')
            item['revision']+=1;db.execute('UPDATE items SET payload=? WHERE id=?',(json.dumps(item),item['id']));self._event(db,pid,'item_updated',dict(before=before,after=item))
        return item
    def manual_item(self,pid,body):
        value=text(body.get('text',''),3000)
        if not value:raise ValueError('Enter the correction text')
        item=dict(id=uid(),label=label(body.get('label'),30),text=value,original_text=None,text_edited=True,source_document=None,source_page=None,status='todo',response='',question='',reference_url='',reference_note='',reference_checked=False,evidence=[],revision=0)
        with self.db() as db:
            self._get(db,'projects',pid)
            if db.execute('SELECT count(*) FROM items WHERE project_id=?',(pid,)).fetchone()[0]>=100:raise ValueError('Maximum 100 items')
            db.execute('INSERT INTO items VALUES(?,?,?)',(item['id'],pid,json.dumps(item)));self._event(db,pid,'manual_item_added',item)
        return item
    def evidence(self,pid,body,remove=False):
        with self.db() as db:
            item=self._get(db,'items',body.get('item_id'),pid);self._revision(item,body)
            if remove:
                old=next((e for e in item['evidence'] if e['id']==body.get('evidence_id')),None)
                if not old:raise ValueError('Evidence not found')
                item['evidence']=[e for e in item['evidence'] if e['id']!=old['id']];self._event(db,pid,'evidence_removed',dict(item_id=item['id'],evidence=old))
            else:
                if len(item['evidence'])>=8:raise ValueError('Maximum eight evidence quotes per item')
                doc=self._get(db,'documents',body.get('document_id'),pid)
                if doc['kind']=='letter':raise ValueError('A correction letter cannot serve as evidence that its own correction is satisfied')
                number=body.get('page')
                if type(number) is not int or not 1<=number<=len(doc['pages']):raise ValueError('Page not found')
                page=doc['pages'][number-1];quote=match_quote(page,body.get('quote'))
                ev=dict(id=uid(),document_id=doc['id'],document_name=doc['name'],page=number,quote=quote,document_sha256=doc['sha256'],page_sha256=page['sha256'],source=doc['source'],checked=body.get('checked') is True)
                if any(e['document_id']==ev['document_id'] and e['page']==number and e['quote']==quote for e in item['evidence']):raise ValueError('This quote is already attached')
                item['evidence'].append(ev);self._event(db,pid,'evidence_attached',dict(item_id=item['id'],evidence=ev))
            if item['status']=='reviewed':item['status']='draft'
            item['revision']+=1;db.execute('UPDATE items SET payload=? WHERE id=?',(json.dumps(item),item['id']))
        return item
    def review_document(self,pid,body):
        with self.db() as db:
            doc=self._get(db,'documents',body.get('id'),pid);doc['reviewed']=body.get('reviewed') is True
            db.execute('UPDATE documents SET payload=? WHERE id=?',(json.dumps(doc),doc['id']));self._event(db,pid,'document_review_changed',dict(id=doc['id'],reviewed=doc['reviewed']))
        return doc
    def review_evidence(self,pid,body):
        with self.db() as db:
            item=self._get(db,'items',body.get('item_id'),pid);self._revision(item,body)
            evidence=next((e for e in item['evidence'] if e['id']==body.get('evidence_id')),None)
            if not evidence:raise ValueError('Evidence not found')
            doc=self._get(db,'documents',evidence['document_id'],pid)
            match_quote(doc['pages'][evidence['page']-1],evidence['quote'])
            evidence['checked']=body.get('checked') is True
            if item['status']=='reviewed':item['status']='draft'
            item['revision']+=1;db.execute('UPDATE items SET payload=? WHERE id=?',(json.dumps(item),item['id']))
            self._event(db,pid,'evidence_review_changed',dict(item_id=item['id'],evidence_id=evidence['id'],checked=evidence['checked']))
        return item
    def update_task(self,pid,body):
        with self.db() as db:
            task=self._get(db,'checklist',body.get('id'),pid);self._revision(task,body);status=body.get('status');note=text(body.get('note',''),2000)
            if status not in ('pending','checked','not_applicable'):raise ValueError('Invalid checklist status')
            if status!='pending' and not note:raise ValueError('Record the review basis or inapplicability reason')
            task.update(status=status,note=note,revision=task['revision']+1);db.execute('UPDATE checklist SET payload=? WHERE id=?',(json.dumps(task),task['id']));self._event(db,pid,'checklist_updated',task)
        return task
    def search(self,pid,query):
        with self.db() as db:
            self._get(db,'projects',pid);docs=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents WHERE project_id=?',(pid,))]
        return search_pages(docs,query)
    def state(self,pid):
        with self.db() as db:
            project=self._get(db,'projects',pid)
            docs=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents WHERE project_id=? ORDER BY rowid',(pid,))]
            items=[json.loads(r[0]) for r in db.execute('SELECT payload FROM items WHERE project_id=? ORDER BY rowid',(pid,))]
            tasks=[json.loads(r[0]) for r in db.execute('SELECT payload FROM checklist WHERE project_id=? ORDER BY rowid',(pid,))]
            events=[dict(seq=r[0],created=r[1],kind=r[2],payload=json.loads(r[3])) for r in db.execute('SELECT seq,created,kind,payload FROM events WHERE project_id=? ORDER BY seq DESC LIMIT 100',(pid,))]
        blockers=[]
        if not items:blockers.append('Add or extract at least one correction item')
        if not any(d['kind']=='plans' for d in docs):blockers.append('Import a plans document or explicitly labeled plan text')
        blockers.extend(f'Item {i["label"]}: not reviewed' for i in items if i['status']!='reviewed')
        blockers.extend(f'{d["name"]}: original document inspection not recorded' for d in docs if not d['reviewed'])
        blockers.extend(f'Checklist: {t["text"]}' for t in tasks if t['status']=='pending')
        for item in items:item['blockers']=item_blockers(item)
        metadata=[{**d,'pages':[dict(number=p['number'],characters=len(p['text']),sha256=p['sha256']) for p in d['pages']]} for d in docs]
        return dict(project=project,documents=metadata,items=items,checklist=tasks,events=events,sources=SOURCES,blockers=blockers,ready_for_professional_review=not blockers)
