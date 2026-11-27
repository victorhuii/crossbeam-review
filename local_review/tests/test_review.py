import io
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader,PdfWriter
from local_review.documents import extract_pdf,text_pages,correction_candidates
from local_review.store import Store
from local_review.demo import seed,plan_pdf,letter_pdf
from local_review.export import markdown,pdf

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'review.db');self.project=seed(self.store);self.pid=self.project['id']
    def tearDown(self):self.tmp.cleanup()
    def state(self):return self.store.state(self.pid)
    def test_pdf_extraction_and_blank_or_encrypted_inputs(self):
        pages,warnings=extract_pdf(plan_pdf());self.assertEqual(len(pages),2);self.assertIn('roof height',pages[1]['text']);self.assertFalse(warnings)
        writer=PdfWriter();writer.add_blank_page(width=200,height=200);out=io.BytesIO();writer.write(out);self.assertTrue(extract_pdf(out.getvalue())[1])
        writer.encrypt('secret');out=io.BytesIO();writer.write(out)
        for raw in (b'not pdf',out.getvalue(),b'%PDF-'+b'x'*8_000_000):
            with self.assertRaises(ValueError):extract_pdf(raw)
    def test_candidates_and_manual_text_source_are_explicit(self):
        pages,_=extract_pdf(letter_pdf());c=correction_candidates(pages);self.assertEqual(len(c),3);self.assertIn('roof height',c[0]['text'])
        doc=self.store.upload(self.pid,'manual-pages.txt','reference',content='An unverified manual page.\fA second manual page.')
        self.assertEqual(doc['source'],'manual_text');self.assertEqual(len(doc['pages']),2);self.assertTrue(doc['warnings'])
    def test_duplicate_import_and_demo_are_idempotent(self):
        self.store.upload(self.pid,'same-plans.pdf','plans',raw=plan_pdf())
        # ReportLab changes document IDs between invocations, so compare the exact stored bytes.
        d=self.state()['documents'][0];raw=self.store.raw(self.pid,d['id']);before=len(self.state()['documents']);self.store.upload(self.pid,d['name'],'plans',raw=raw)
        self.assertEqual(len(self.state()['documents']),before);self.assertEqual(seed(self.store)['id'],self.pid)
    def test_provenance_quote_and_project_isolation(self):
        item=self.state()['items'][2];doc=self.state()['documents'][0]
        with self.assertRaises(ValueError):self.store.evidence(self.pid,dict(item_id=item['id'],revision=0,document_id=doc['id'],page=2,quote='This text is not on the page',checked=True))
        other=self.store.create(dict(name='Other',jurisdiction='Elsewhere',adu_type='conversion',area_sqft=400))
        with self.assertRaises(ValueError):self.store.page(other['id'],doc['id'],1)
        with self.assertRaises(ValueError):self.store.evidence(other['id'],dict(item_id=item['id'],revision=0,document_id=doc['id'],page=2,quote='Proposed roof height is 12 feet in this fictional example.',checked=True))
        self.assertFalse(self.state()['ready_for_professional_review'])
    def test_review_requires_response_checked_evidence_and_explicit_confirmation(self):
        item=self.state()['items'][0]
        base=dict(id=item['id'],revision=item['revision'],status='reviewed',response='Response written',question='',confirm_review=True)
        with self.assertRaises(ValueError):self.store.update_item(self.pid,base)
        # Replace unchecked evidence with a deliberately checked fictional-source quote.
        item=self.store.evidence(self.pid,dict(item_id=item['id'],revision=item['revision'],evidence_id=item['evidence'][0]['id']),remove=True)
        doc=self.state()['documents'][0];item=self.store.evidence(self.pid,dict(item_id=item['id'],revision=item['revision'],document_id=doc['id'],page=2,quote='Proposed roof height is 12 feet in this fictional example.',checked=True))
        base['revision']=item['revision'];base['confirm_review']=False
        with self.assertRaises(ValueError):self.store.update_item(self.pid,base)
        base['confirm_review']=True;reviewed=self.store.update_item(self.pid,base);self.assertEqual(reviewed['status'],'reviewed')
        reopened=self.store.evidence(self.pid,dict(item_id=reviewed['id'],revision=reviewed['revision'],evidence_id=reviewed['evidence'][0]['id']),remove=True)
        self.assertEqual(reopened['status'],'draft')
    def test_stale_updates_and_reference_checks_fail_closed(self):
        item=self.state()['items'][0]
        with self.assertRaises(ValueError):self.store.update_item(self.pid,dict(id=item['id'],revision=0,status='draft',response='x'))
        with self.assertRaises(ValueError):self.store.update_item(self.pid,dict(id=item['id'],revision=item['revision'],status='draft',response='x',reference_url='javascript:alert(1)'))
        self.assertEqual(self.state()['items'][0]['response'],item['response'])
    def test_search_is_only_candidate_text_and_excludes_letter(self):
        results=self.store.search(self.pid,'roof height elevation');self.assertTrue(results);self.assertTrue(all(r['name']!='fictional-corrections.pdf' for r in results));self.assertTrue(any(r['page']==2 for r in results))
    def test_reference_needs_checked_applicability_and_written_basis(self):
        item=self.state()['items'][0];e=item['evidence'][0]
        item=self.store.review_evidence(self.pid,dict(item_id=item['id'],revision=item['revision'],evidence_id=e['id'],checked=True))
        body=dict(id=item['id'],revision=item['revision'],status='reviewed',response='Fictional draft only',question='',confirm_review=True,reference_url='https://www.hcd.ca.gov/building-standards/adu',reference_checked=False,reference_note='')
        with self.assertRaisesRegex(ValueError,'applicability'):self.store.update_item(self.pid,body)
        body['reference_checked']=True
        with self.assertRaisesRegex(ValueError,'basis'):self.store.update_item(self.pid,body)
        body['reference_note']='Fictional test basis only; not an actual legal interpretation'
        self.assertEqual(self.store.update_item(self.pid,body)['status'],'reviewed')
    def test_checklist_needs_basis_and_scoped_categories(self):
        task=self.state()['checklist'][0]
        with self.assertRaises(ValueError):self.store.update_task(self.pid,dict(id=task['id'],revision=0,status='not_applicable',note=''))
        t=self.store.update_task(self.pid,dict(id=task['id'],revision=0,status='checked',note='Fictional test review only'))
        self.assertEqual(t['status'],'checked');self.assertFalse(self.state()['ready_for_professional_review'])
    def test_draft_exports_preserve_open_questions_and_provenance(self):
        state=self.state();m=markdown(state);self.assertIn('DRAFT',m);self.assertIn('missing designer signature',m);self.assertIn('Page SHA-256',m)
        raw=pdf(state);reader=PdfReader(io.BytesIO(raw));content='\n'.join(p.extract_text() for p in reader.pages)
        self.assertIn('PROFESSIONAL REVIEW',content);self.assertIn('missing designer signature',content);self.assertIn('fictional-plans.pdf',content)
    def test_audit_and_original_document_survive_restart(self):
        fresh=Store(self.store.path);state=fresh.state(self.pid);self.assertTrue(state['events']);self.assertTrue(fresh.raw(self.pid,state['documents'][0]['id']).startswith(b'%PDF-'));self.assertEqual(len(state['items']),3)

class CompletionTests(unittest.TestCase):
    setUp=ReviewTests.setUp
    tearDown=ReviewTests.tearDown
    state=ReviewTests.state
    def test_editable_working_text_preserves_the_original(self):
        item=self.state()['items'][0];original=item['text']
        changed=self.store.update_item(self.pid,dict(id=item['id'],revision=item['revision'],status='draft',response='Draft',correction_text='Reviewer clarification of the roof-height request',label='1 revised'))
        self.assertEqual(changed['original_text'],original);self.assertTrue(changed['text_edited'])
        self.assertIn('Original extracted text',markdown(self.state()))
    def test_full_workflow_can_complete_without_becoming_an_approval(self):
        doc=self.state()['documents'][0]
        for item in self.state()['items']:
            if not item['evidence']:
                item=self.store.evidence(self.pid,dict(item_id=item['id'],revision=item['revision'],document_id=doc['id'],page=2,quote='Proposed roof height is 12 feet in this fictional example.',checked=False))
            for evidence in list(item['evidence']):
                item=self.store.review_evidence(self.pid,dict(item_id=item['id'],revision=item['revision'],evidence_id=evidence['id'],checked=True))
            self.store.update_item(self.pid,dict(id=item['id'],revision=item['revision'],status='reviewed',response='Fictional workflow assertion only; not a compliance finding.',question='',confirm_review=True))
        for d in self.state()['documents']:self.store.review_document(self.pid,dict(id=d['id'],reviewed=True))
        for task in self.state()['checklist']:self.store.update_task(self.pid,dict(id=task['id'],revision=task['revision'],status='checked',note='Fictional automated test declaration only'))
        state=self.state();self.assertTrue(state['ready_for_professional_review']);self.assertFalse(state['blockers']);self.assertNotIn('approved',state)
        self.store.review_document(self.pid,dict(id=doc['id'],reviewed=False));self.assertFalse(self.state()['ready_for_professional_review'])

if __name__=='__main__':unittest.main()
