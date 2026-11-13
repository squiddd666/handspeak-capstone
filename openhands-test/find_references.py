"""Find public video reference links; no bulk video redistribution."""
import json,re,html,urllib.request,concurrent.futures,datetime,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
labels=json.loads((ROOT/'third_party/OpenHands-source/api/data/labels/word_labels_100.json').read_text())
tested={r['expected'] for r in json.loads((ROOT/'openhands-test/reference-results.json').read_text())['rows']}
splits=json.loads((ROOT/'third_party/OpenHands-source/api/data/splits/asl100.json').read_text())
indexed={x['gloss']:x['instances'] for x in splits}
def fetch(url,video=False):
    headers={'User-Agent':'Mozilla/5.0'}
    if video:headers['Range']='bytes=0-63'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as r:
        data=r.read(64 if video else 2000000)
        return r.status,r.headers.get('Content-Type',''),data
def find(word):
    page='https://www.signasl.org/sign/'+word
    row=dict(word=word,page=page,page_verified=False,video=None,video_verified=False,wlasl_candidates=[dict(url=x['url'],video_id=x['video_id'],original_split=x['split'],frame_start=x.get('frame_start'),frame_end=x.get('frame_end')) for x in indexed.get(word,[])[:3]])
    try:
        status,mime,data=fetch(page)
        text=data.decode('utf-8','replace')
        sources=[html.unescape(u) for u in re.findall(r'<source[^>]+src=["\']([^"\']+)',text)]
        row['page_verified']=status==200 and bool(sources)
        row['video_count']=len(sources)
        for url in sources[:3]:
            try:
                code,kind,head=fetch(url,True)
                if code in (200,206) and ('video/' in kind or b'ftyp' in head):
                    row.update(video=url,video_verified=True);break
            except Exception:pass
        if not row['video'] and sources:row['video']=sources[0]
    except Exception as e:row['error']=str(e)
    print(word,'page',row['page_verified'],'video',row['video_verified'],flush=True)
    return row
missing=[w for w in labels if w not in tested]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    rows=list(pool.map(find,missing))
report=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),count=len(rows),verified_video_count=sum(r['video_verified'] for r in rows),verified_page_count=sum(r['page_verified'] for r in rows),note='Reference links only. HTTP/media checks are not human verification of sign meaning or full video playback. Licenses remain with source owners. WLASL candidates are metadata only and may overlap OpenHands training, regardless of original split. These links have not been used in a new accuracy evaluation.',rows=rows)
(ROOT/'openhands-reference-videos.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
with (ROOT/'openhands-test/reference-links.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=['word','page','page_verified','video','video_verified']);writer.writeheader();writer.writerows({k:r.get(k) for k in writer.fieldnames} for r in rows)
items=[]
for r in rows:
    esc=html.escape
    items.append(f'<tr><td>{esc(r["word"].upper())}</td><td><a href="{esc(r["page"])}" target="_blank" rel="noopener">Dictionary &amp; variants</a></td><td>'+ (f'<a href="{esc(r["video"])}" target="_blank" rel="noopener">Watch video</a>' if r['video'] else 'Unavailable')+f'</td><td>{"Media checked" if r["video_verified"] else "Needs checking"}</td></tr>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OpenHands — 69 remaining word references</title><style>body{background:#0a120e;color:#dceee3;font:15px/1.6 system-ui;margin:32px auto;max-width:1050px;padding:0 20px}h1,a{color:#00e9a5}p{color:#a2b8aa}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #294333}a{text-underline-offset:4px}td:first-child{font-weight:700}@media(max-width:600px){td,th{padding:8px;font-size:12px}}</style><a href="http://localhost:8001">← OpenHands local test</a><h1>69 remaining ASL word references</h1>'''
page+=f'<p>Found {len(rows)} word entries; {report["verified_video_count"]} video URLs passed a media availability check. Checked {report["checked_utc"][:10]} (UTC).</p><p>These are learning references, not a clean test set. Sign variants and meanings need review. Some dictionary videos may also occur in WLASL training data. No new model accuracy result is claimed. Videos stay hosted by their original providers; no redistribution rights are implied.</p><table><thead><tr><th>Word</th><th>Source</th><th>Video</th><th>Check</th></tr></thead><tbody>'+''.join(items)+'</tbody></table></html>'
(ROOT/'openhands-references.html').write_text(page,encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
