"""Optional visual QA and portfolio preview of the fictional exported PDF."""
from pathlib import Path
import pymupdf
root=Path(__file__).resolve().parents[1];out=root/'docs/assets';out.mkdir(parents=True,exist_ok=True)
doc=pymupdf.open(root/'examples/fictional-response-draft.pdf')
for i,page in enumerate(doc):page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(out/f'response-draft-page-{i+1}.png')
print('Rendered',len(doc),'fictional response pages')
