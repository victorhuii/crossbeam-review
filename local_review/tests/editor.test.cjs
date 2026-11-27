const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const os=require('node:os');const vm=require('node:vm');const {spawn}=require('node:child_process');const {once}=require('node:events');const readline=require('node:readline');
const root=path.resolve(__dirname,'../..');
async function harness(){
 const {Window}=await import('happy-dom');const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'crossbeam-ui-'));const python=process.env.CROSSBEAM_PYTHON||'python3';
 const child=spawn(python,['-u','-m','local_review.server','--demo','--data',path.join(tmp,'db'),'--port','0'],{cwd:root,stdio:['ignore','pipe','pipe']});let errors='';child.stderr.on('data',d=>errors+=d.toString());const lines=readline.createInterface({input:child.stdout});
 let line;try{[line]=await once(lines,'line',{signal:AbortSignal.timeout(8000)});}catch(e){child.kill('SIGKILL');throw Error(errors||e.message);}
 const base=line.split('CrossBeam Review: ')[1];const window=new Window({url:base,settings:{disableJavaScriptEvaluation:true,disableCSSFileLoading:true,disableJavaScriptFileLoading:true}});window.document.write(fs.readFileSync(path.join(root,'local_review/web/index.html'),'utf8'));
 const context=vm.createContext({window,document:window.document,FormData:window.FormData,FileReader:window.FileReader,URL,URLSearchParams,Date,JSON,Map,Error,console,fetch:(url,options)=>fetch(new URL(url,base),options)});
 vm.runInContext(fs.readFileSync(path.join(root,'local_review/web/app.js'),'utf8'),context);
 const wait=async()=>{for(let n=0;n<250;n++){if(!vm.runInContext('busy',context))return;await new Promise(r=>setTimeout(r,10));}throw Error('UI request timed out: '+errors);};await wait();
 return {window,doc:window.document,context,base,wait,state:()=>vm.runInContext('state',context),event(type){return new window.Event(type,{bubbles:true,cancelable:true});},async close(){await window.happyDOM.abort();window.close();lines.close();if(child.exitCode===null){child.kill('SIGINT');await once(child,'exit',{signal:AbortSignal.timeout(5000)});}fs.rmSync(tmp,{recursive:true,force:true});}};
}
test('real HTTP review preserves unsaved response edits and enforces human confirmation',async()=>{const h=await harness();try{
 assert.match(h.doc.getElementById('summary').textContent,/13 workflow checks open/);
 let form=h.doc.getElementById('response-form');form.elements.response.value='Fictional DOM draft retained through evidence updates.';form.elements.response.dispatchEvent(h.event('input'));
 const check=h.doc.querySelector('[data-check-evidence]');check.checked=true;check.dispatchEvent(h.event('change'));await h.wait();assert.equal(h.state().items[0].evidence[0].checked,true);assert.match(h.doc.getElementById('response-form').elements.response.value,/DOM draft retained/);
 form=h.doc.getElementById('response-form');form.elements.status.value='reviewed';form.dispatchEvent(h.event('submit'));await h.wait();assert.match(h.doc.getElementById('message').textContent,/Explicitly confirm human review/);assert.equal(h.state().items[0].status,'draft');
 form=h.doc.getElementById('response-form');assert.equal(form.elements.status.value,'reviewed','Selected reviewed state should survive a validation failure');form.elements.confirm_review.checked=true;form.dispatchEvent(h.event('submit'));await h.wait();assert.equal(h.state().items[0].status,'reviewed',h.doc.getElementById('message').textContent);assert.equal(h.state().ready_for_professional_review,false);
 }finally{await h.close();}});
test('candidate quotes and manually added text use the real backend and remain inert',async()=>{const h=await harness();try{
 h.doc.getElementById('query').value='roof height elevation';h.doc.getElementById('search-form').dispatchEvent(h.event('submit'));await h.wait();assert.ok(h.doc.querySelector('[data-candidate]'));h.doc.querySelector('[data-candidate]').click();const evidence=h.doc.getElementById('evidence-form');assert.ok(evidence.elements.quote.value.includes('roof height'));assert.equal(evidence.elements.checked.checked,false);
 const form=h.doc.getElementById('new-item-form');form.elements.label.value='X';form.elements.text.value='<img src=x onerror=bad()> Check this manually';form.dispatchEvent(h.event('submit'));await h.wait();assert.equal(h.state().items.length,4);assert.equal(h.doc.querySelector('#response img'),null);assert.match(h.doc.querySelector('#response .quote').textContent,/<img/);
 }finally{await h.close();}});
test('document pages, inspection notes, checklist saves and PDF export work end to end',async()=>{const h=await harness();try{
 const did=h.state().documents[0].id;h.doc.getElementById('page-document').value=did;h.doc.getElementById('page-number').value='2';h.doc.getElementById('page-form').dispatchEvent(h.event('submit'));await h.wait();assert.match(h.doc.getElementById('page-text').textContent,/roof height/);
 const inspect=h.doc.querySelector('[data-document-review]');inspect.checked=true;inspect.dispatchEvent(h.event('change'));await h.wait();assert.equal(h.state().documents[0].reviewed,true);
 const task=h.doc.querySelector('[data-task]');task.elements.status.value='checked';task.elements.note.value='Inspected fictional fixture only.';task.dispatchEvent(h.event('submit'));await h.wait();assert.equal(h.state().checklist[0].status,'checked');
 const url=new URL('/api/export',h.base);url.searchParams.set('project',h.state().project.id);url.searchParams.set('format','pdf');const response=await fetch(url);assert.equal(response.status,200);assert.equal(Buffer.from(await response.arrayBuffer()).subarray(0,5).toString(),'%PDF-');
 }finally{await h.close();}});
