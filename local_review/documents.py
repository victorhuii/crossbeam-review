"""Bounded local document text extraction and editable correction candidates."""
import hashlib
import io
import re

MAX_PDF=8_000_000
MAX_PAGES=100
MAX_TEXT=500_000

def digest(data):return hashlib.sha256(data).hexdigest()
def normalize(text):return ' '.join(text.split())
def label(value,maximum=150):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum or any(ord(c)<32 for c in value):raise ValueError('A plain nonempty label is required')
    return value.strip()

def extract_pdf(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_PDF or not raw.startswith(b'%PDF-'):raise ValueError('Choose a PDF no larger than 8 MB')
    from pypdf import apply_configuration
    with apply_configuration(maximum_declared_stream_length=8_000_000,zlib_maximum_output_length=8_000_000,lzw_maximum_output_length=8_000_000,run_length_maximum_output_length=8_000_000,array_based_stream_maximum_output_length=8_000_000,stream_decoding_work_maximum_length=16_000_000,stream_parsing_work_maximum_count=500_000,page_tree_maximum_page_entries=1000,xform_maximum_invocations_per_extraction=500):
        return _extract_pdf(raw)

def _extract_pdf(raw):
    from pypdf import PdfReader
    try:reader=PdfReader(io.BytesIO(raw),strict=True)
    except Exception as exc:raise ValueError('PDF could not be read') from exc
    if reader.is_encrypted:raise ValueError('Encrypted PDFs are not supported; provide an unlocked local copy')
    if not 1<=len(reader.pages)<=MAX_PAGES:raise ValueError('PDF must contain 1–100 pages')
    pages=[];total=0;warnings=[]
    for number,page in enumerate(reader.pages,1):
        try:
            content=page.get_contents()
            if content and len(content.get_data())>2_000_000:raise ValueError('page content stream exceeds 2 MB')
            text=(page.extract_text() or '').replace('\x00','')
        except Exception as exc:raise ValueError(f'Could not extract page {number}; provide a text copy instead') from exc
        total+=len(text)
        if len(text)>30_000 or total>MAX_TEXT:raise ValueError('Extracted text is too large; split the document')
        if len(normalize(text))<12:warnings.append(f'Page {number} has little or no extractable text. Drawings/scans require human inspection; no OCR ran.')
        pages.append(dict(number=number,text=text,sha256=digest(text.encode())))
    return pages,warnings

def text_pages(text):
    if not isinstance(text,str) or not text.strip() or len(text)>MAX_TEXT:raise ValueError('Provide 1–500,000 characters of text')
    chunks=text.split('\f')
    if len(chunks)>MAX_PAGES:raise ValueError('Maximum 100 text pages separated by form feeds')
    pages=[]
    for n,chunk in enumerate(chunks,1):
        if len(chunk)>30_000:raise ValueError('Text pages are limited to 30,000 characters')
        pages.append(dict(number=n,text=chunk,sha256=digest(chunk.encode())))
    return pages,['User-supplied text and page numbering are not authenticated against an original PDF.']

def correction_candidates(pages):
    candidates=[]
    pattern=re.compile(r'^\s*((?:\d+(?:\.\d+)*|[A-Z])[.)])\s+(.+)$')
    for page in pages:
        current=None
        for line in page['text'].splitlines():
            match=pattern.match(line)
            if match:
                if current:candidates.append(current)
                current=dict(label=match[1],text=match[2].strip(),page=page['number'])
            elif current and line.strip():current['text']+=' '+line.strip()
        if current:candidates.append(current)
    if not candidates:
        candidates=[dict(label=f'Page {p["number"]}',text=normalize(p['text']),page=p['number']) for p in pages if normalize(p['text'])]
    if len(candidates)>80:raise ValueError('More than 80 candidate items; split the corrections document')
    for c in candidates:
        if len(c['text'])>3000:raise ValueError('A correction candidate is too long; import manually edited text instead')
    return candidates

def match_quote(page,quote):
    if not isinstance(quote,str) or not 8<=len(quote)<=1000:raise ValueError('Evidence quote must contain 8–1000 characters')
    if normalize(quote) not in normalize(page['text']):raise ValueError('Quote does not match the selected document page')
    return quote.strip()

def search_pages(documents,query):
    if not isinstance(query,str) or len(query)>200:raise ValueError('Search is limited to 200 characters')
    stop={'the','and','for','that','with','this','show','provide','please','from','shall','must','have'}
    terms={w.lower() for w in re.findall(r'[A-Za-z0-9]{3,}',query) if w.lower() not in stop}
    if not terms:return []
    found=[]
    for doc in documents:
        if doc['kind']=='letter':continue
        for p in doc['pages']:
            low=p['text'].lower();score=sum(min(3,len(re.findall(re.escape(t),low))) for t in terms)
            if score:
                first=min(low.find(t) for t in terms if t in low);start=max(0,first-50);snippet=p['text'][start:start+400]
                found.append(dict(document_id=doc['id'],name=doc['name'],page=p['number'],score=score,quote=snippet,source=doc['source']))
    return sorted(found,key=lambda x:(-x['score'],x['document_id'],x['page']))[:8]
