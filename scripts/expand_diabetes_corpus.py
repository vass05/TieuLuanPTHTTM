"""Build-time source discovery/review for the public diabetes education corpus.

Raw pages and draft responses stay in the gitignored checkpoint directory.
Nothing crawls the web at chat runtime. Provider credentials are never exported.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.ipynb_checkpoints'/'diabetes-expansion'
HOSTS={'www.niddk.nih.gov','www.cdc.gov','diabetes.org','www.diabetes.org.uk','www.nhs.uk','www.nccih.nih.gov'}
DRUGS=['metformin','gliclazide','glimepiride','glipizide','pioglitazone','sitagliptin','linagliptin',
    'saxagliptin','alogliptin','dapagliflozin','empagliflozin','canagliflozin','ertugliflozin',
    'semaglutide','liraglutide','dulaglutide','exenatide','tirzepatide','insulin','glucagon']
SEEDS=[
    'https://www.niddk.nih.gov/health-information/diabetes/overview',
    'https://www.cdc.gov/diabetes/about/index.html',
    'https://www.cdc.gov/diabetes/living-with/index.html',
    'https://www.cdc.gov/diabetes/healthy-eating/index.html',
    'https://www.cdc.gov/diabetes/diabetes-complications/index.html',
    'https://diabetes.org/food-nutrition',
    'https://diabetes.org/health-wellness',
    'https://www.diabetes.org.uk/living-with-diabetes/eating',
    'https://www.diabetes.org.uk/living-with-diabetes',
    'https://www.diabetes.org.uk/about-diabetes',
    'https://www.nhs.uk/conditions/type-2-diabetes/',
    'https://www.nhs.uk/conditions/type-1-diabetes/',
    'https://www.nhs.uk/conditions/gestational-diabetes/',
    'https://www.nccih.nih.gov/health/diabetes-and-dietary-supplements-what-you-need-to-know',
    'https://diabetes.org/food-nutrition/reading-food-labels/fruit',
    'https://www.diabetes.org.uk/living-with-diabetes/eating/fruit-and-diabetes',
]+['https://www.nhs.uk/medicines/'+drug+'/' for drug in DRUGS]


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def relevant(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS or parsed.query:return False
    path=parsed.path
    if re.search(r'\.(pdf|jpg|png|svg|zip)$|/es/|/spanish/|/news|/research|/events|/donate',path):return False
    if parsed.hostname=='www.nhs.uk':
        return any('/medicines/'+d+'/' in path for d in DRUGS) or bool(re.match(
            r'/conditions/(?:type-1-diabetes|type-2-diabetes|gestational-diabetes|diabetic-|low-blood-sugar|high-blood-sugar)',path))
    return any(p in path for p in ('/health-information/diabetes/','/diabetes/','/food-nutrition',
        '/health-wellness','/living-with-diabetes','/about-diabetes','/health/diabetes'))


def fetch(url):
    try:
        response=requests.get(url,timeout=(5,18),headers={'User-Agent':'DiabetesEducationProject/1.0 (source verification)'})
        if response.status_code!=200 or not relevant(response.url):return None
        soup=BeautifulSoup(response.content,'html.parser')
        h1=soup.find('h1')
        if not h1:return None
        title=h1.get_text(' ',strip=True)
        main=soup.find('main') or soup.find('article') or soup.body
        for node in main.select('nav,header,footer,aside,script,style,noscript,form,button'):
            node.decompose()
        lines=[n.get_text(' ',strip=True) for n in main.select('h1,h2,h3,p,li')]
        # Nested list text is not repeated in the saved excerpt.
        lines=list(dict.fromkeys(line for line in lines if len(line)>16))
        body='\n'.join(lines)
        if len(body)<350:return None
        links=sorted({urljoin(response.url,a['href']).split('#')[0] for a in soup.find_all('a',href=True)})
        return dict(url=response.url.split('?')[0],title=title,text=body,
            source_sha256=hashlib.sha256(response.content).hexdigest(),
            retrieved_on='2026-10-31',http_status=200,links=[u for u in links if relevant(u)])
    except requests.RequestException:
        return None


def discover():
    CACHE.mkdir(parents=True,exist_ok=True)
    pages={};attempted=set();todo=list(SEEDS)
    for depth in range(3):
        queue=[u for u in todo if u not in attempted][:360]
        attempted.update(queue)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(fetch,queue):
                if result:
                    pages[result['url']]=result
        dump(CACHE/'sources.json',list(pages.values()))
        print(json.dumps(dict(depth=depth,pages=len(pages),attempted=len(attempted))),flush=True)
        todo=sorted({link for page in pages.values() for link in page['links']} - attempted)
        if len(pages)>=220:break
    catalog=[dict(url=p['url'],title=p['title'],characters=len(p['text'])) for p in pages.values()]
    dump(CACHE/'catalog.json',catalog)
    print(json.dumps(dict(host_counts={h:sum(urlparse(p['url']).hostname==h for p in pages.values()) for h in HOSTS})),flush=True)


def category(url):
    if any(s in url for s in ('/food-nutrition/','/eating/')):return 'nutrition'
    if '/medicines/' in url or '/medication/' in url or '/treatments/' in url:return 'medicines'
    if re.search(r'a1c|hba1c|blood-sugar|technology|devices|diagnosis|sick-days|ketones|time-in-range',url):return 'monitoring'
    if re.search(r'gestational|pregnancy|baby',url):return 'pregnancy'
    if re.search(r'complications|neuropath|retinopathy|kidney|hypo|hyper|pancreatic',url):return 'complications'
    if re.search(r'fitness|mental|weight|smoking|sexual|supporting|children|driving|exercise',url):return 'lifestyle'
    return 'general'


def select_sources():
    rows=json.loads((CACHE/'sources.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'knowledge/diabetes_extended.json').read_text(encoding='utf-8'))['documents']
    old+=json.loads((ROOT/'model/agents/knowledge_documents.json').read_text(encoding='utf-8'))
    existing={r['source_url'].rstrip('/') for r in old}
    banned=r'all-content|common-terms|statistics|cooking-classes|clinical-trials|/recipes/|champion-corner|better-choices-for-life|informacion-de-la-salud|/how-and-when-|can-i-get-cgm|financial-help|driving-licence'
    candidates=[r for r in rows if r['url'].rstrip('/') not in existing and len(r['text'])>=1100 and not re.search(banned,r['url'])]
    buckets={c:[] for c in ('nutrition','medicines','monitoring','pregnancy','complications','lifestyle','general')}
    for row in candidates:buckets[category(row['url'])].append(row)
    for values in buckets.values():values.sort(key=lambda r:(-r['url'].count('/'),r['url']))
    # Cover common oral/injectable medicines before subtype-specific insulin
    # pages, rather than filling the medicine allocation with similar leaf pages.
    medicine_urls=[
        'https://www.diabetes.org.uk/about-diabetes/looking-after-diabetes/treatments/insulin/types',
        'https://www.diabetes.org.uk/about-diabetes/looking-after-diabetes/treatments/insulin/what-is-insulin',
        'https://www.diabetes.org.uk/about-diabetes/looking-after-diabetes/treatments/tablets-and-medication/sulphonylureas',
    ]+['https://www.nhs.uk/medicines/'+drug+'/' for drug in
        ['gliclazide','sitagliptin','linagliptin','alogliptin','dapagliflozin','empagliflozin','semaglutide','liraglutide','tirzepatide']]+[
        'https://www.nhs.uk/medicines/insulin/'+kind+'/about-'+kind+'/' for kind in
        ['biphasic-insulin','intermediate-acting-insulin','long-acting-insulin','rapid-acting-insulin','short-acting-insulin']]+[
        'https://www.nhs.uk/medicines/insulin/long-acting-insulin/'+leaf+'/' for leaf in
        ['storing-and-travelling-with-long-acting-insulin','taking-long-acting-insulin-with-other-medicines-and-herbal-supplements',
         'pregnancy-breastfeeding-and-fertility-while-taking-long-acting-insulin']]
    by_url={r['url']:r for r in buckets['medicines']}
    if any(u not in by_url for u in medicine_urls):raise ValueError('A required medicine source was not verified')
    buckets['medicines']=[by_url[u] for u in medicine_urls]+[r for r in buckets['medicines'] if r['url'] not in medicine_urls]
    pinned='https://www.diabetes.org.uk/living-with-diabetes/eating/fruit-and-diabetes'
    selected=[next(r for r in candidates if r['url']==pinned)]
    limits=dict(nutrition=27,medicines=20,monitoring=18,pregnancy=12,complications=25,lifestyle=20,general=4)
    for c,limit in limits.items():
        chosen=[r for r in buckets[c] if r['url']!=pinned][:limit-(c=='nutrition')]
        selected.extend(chosen)
    if len(selected)<126:
        urls={r['url'] for r in selected}
        selected.extend(r for r in candidates if r['url'] not in urls)
    selected=selected[:126]
    if len(selected)!=126:raise ValueError('Not enough distinct substantive source pages')
    for i,row in enumerate(selected,33):
        row.update(doc_id=f'K{i:02d}',category=category(row['url']))
    dump(CACHE/'selected.json',selected)
    print(json.dumps(dict(selected=len(selected),categories={c:sum(r['category']==c for r in selected) for c in buckets})))


def generate_json(system,value):
    from dotenv import dotenv_values
    env=dotenv_values(ROOT/'.env')
    key=os.environ.get('GEMINI_API_KEY') or env.get('GEMINI_API_KEY')
    model=os.environ.get('CORPUS_BUILD_MODEL') or os.environ.get('ASSISTANT_GEMINI_MODEL') or env.get('ASSISTANT_GEMINI_MODEL') or 'gemini-3.5-flash-lite'
    if not key:raise ValueError('Missing server credential')
    doc_schema={'type':'OBJECT','properties':{k:{'type':'STRING'} for k in ('doc_id','title','topic','summary_vi')}}
    doc_schema['properties'].update(aliases={'type':'ARRAY','items':{'type':'STRING'}},
        facts={'type':'ARRAY','items':{'type':'ARRAY','items':{'type':'STRING'}}},
        support_quotes={'type':'ARRAY','items':{'type':'STRING'}})
    doc_schema['required']=list(doc_schema['properties'])
    schema={'type':'OBJECT','properties':{'documents':{'type':'ARRAY','items':doc_schema},
        'review':{'type':'ARRAY','items':{'type':'OBJECT','properties':{'doc_id':{'type':'STRING'},
            'changed':{'type':'BOOLEAN'},'note':{'type':'STRING'}},'required':['doc_id','changed','note']}}},'required':['documents']}
    response=requests.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
        headers={'x-goog-api-key':key,'Content-Type':'application/json'},timeout=(5,55),allow_redirects=False,
        json={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'parts':[{'text':json.dumps(value,ensure_ascii=False)}]}],
            'generationConfig':{'temperature':.1,'maxOutputTokens':18000,'responseMimeType':'application/json','responseSchema':schema}})
    if response.status_code!=200:raise ValueError('Provider status '+str(response.status_code))
    data=response.json()
    parts=data['candidates'][0]['content']['parts']
    dump(CACHE/'last-provider-metadata.json',dict(finish_reason=data['candidates'][0].get('finishReason'),
        characters=sum(len(p.get('text','')) for p in parts)))
    text=''.join(p.get('text','') for p in parts if not p.get('thought'))
    try:return json.loads(text)
    except json.JSONDecodeError:
        (CACHE/'last-invalid-response.txt').write_text(text,encoding='utf-8')
        # Parse harmless trailing commas/unquoted object keys as data only.
        # The full schema and source checks still run on the result.
        import json5
        return json5.loads(text)


def validate_draft(doc,source):
    if doc.get('doc_id')!=source['doc_id']:raise ValueError('Incorrect source identifier')
    if not 35<=len(doc.get('summary_vi','').split())<=125:raise ValueError('Summary length outside review budget')
    if not 3<=len(doc.get('aliases',[]))<=8:raise ValueError('Missing topic aliases')
    if not 2<=len(doc.get('facts',[]))<=4 or any(len(f)!=3 for f in doc['facts']):raise ValueError('Invalid graph facts')
    quotes=doc.get('support_quotes',[])
    if not quotes or sum(len(q.split()) for q in quotes)>22:raise ValueError('Quotation limit exceeded')
    source_text=' '.join(source['text'].split())
    if any(len(q)<20 or ' '.join(q.split()) not in source_text for q in quotes):raise ValueError('Support quote does not occur in source')
    words=len((doc['title']+' '+doc['summary_vi']+' '+' '.join(doc['aliases'])+' '+' '.join(' '.join(f) for f in doc['facts'])+' '+' '.join(quotes)).split())
    if words>195:raise ValueError('Source paraphrase budget exceeded')
    text=doc['summary_vi'].lower()
    if re.search(r'\d\s*(?:mg|mcg|µg|ml|iu)\b(?!\s*/)',text):raise ValueError('Prescription dosing is excluded')
    if 'http' in text:raise ValueError('Unexpected source URL in prose')
    for field in ('title','topic','summary_vi'):
        if not isinstance(doc.get(field),str) or not doc[field].strip():raise ValueError('Missing document field')


def checked_generation(system,values,batch):
    by_id={r['doc_id']:r for r in batch}
    request=values
    for attempt in range(3):
        try:result=generate_json(system,request)
        except (json.JSONDecodeError,requests.RequestException,ValueError) as exc:
            if isinstance(exc,ValueError) and str(exc).startswith('Provider status 4') and '429' not in str(exc):raise
            print(json.dumps(dict(retry=attempt+1,errors=['Provider returned an incomplete response; retrying batch.'])),flush=True)
            time.sleep(min(3*(attempt+1),9))
            continue
        errors=[]
        docs=result.get('documents',[])
        if {d.get('doc_id') for d in docs}!=set(by_id):errors.append('Return each requested doc_id exactly once.')
        for doc in docs:
            quotes=doc.get('support_quotes',[])
            options=quote_options(by_id.get(doc.get('doc_id'),{}).get('text',''))
            quotes=[options.get(q,q) for q in quotes]
            if len(quotes)>2:quotes=quotes[:2]
            budget=20//max(len(quotes),1)
            doc['support_quotes']=[' '.join(q.split()[:budget]) for q in quotes]
            try:validate_draft(doc,by_id[doc['doc_id']])
            except (ValueError,KeyError) as exc:errors.append(doc.get('doc_id','?')+': '+str(exc))
        if not errors:return result
        dump(CACHE/'last-validation-retry.json',dict(errors=errors,result=result))
        print(json.dumps(dict(retry=attempt+1,errors=errors)),flush=True)
        request=dict(materials=values,previous_output=result,validation_errors=errors,
            instruction='Correct ALL validation issues, keep every document, return the same complete JSON structure. Prefer 70-word summaries and short quotes copied exactly.')
    raise ValueError('Source/length validation failed after three attempts')


def quote_options(text):
    sentences=re.split(r'(?<=[.!?])\s+|\n',text[:18000])
    snippets=[]
    for sentence in sentences:
        words=sentence.split()
        if len(words)>=7:
            snippet=' '.join(words[:10])
            if snippet not in snippets:snippets.append(snippet)
    return {f'Q{i:03d}':value for i,value in enumerate(snippets[:180],1)}


def draft():
    selected=json.loads((CACHE/'selected.json').read_text(encoding='utf-8'))
    system=('Soạn thẻ kiến thức giáo dục tiểu đường tiếng Việt, CHỈ dùng nội dung của từng nguồn tương ứng. '
        'Không thêm hiểu biết bên ngoài, liều thuốc, hướng dẫn đổi/ngừng thuốc, hoặc chẩn đoán cá nhân. '
        'Mỗi trang là một tài liệu với trọng tâm riêng cụ thể từ nội dung trang; không viết lại cùng một tổng quan chung. '
        'Chỉ trả JSON {"documents":[...]}. Mỗi tài liệu có doc_id đúng đầu vào, title tiếng Việt, topic snake_case tiếng Anh, '
        'summary_vi khoảng 65–100 từ tính theo khoảng trắng (tối đa 125), trả lời trọng tâm rồi giải thích ngắn; '
        'aliases 3–6 cụm hỏi/từ khóa tiếng Việt cụ thể cho chủ đề (tránh từ chung như tiểu đường, insulin, thuốc, ăn uống), '
        'facts 2 hoặc 3 bộ [chủ thể,quan hệ,đối tượng] NGẮN BẰNG TIẾNG VIỆT có trong nguồn, '
        'support_quotes là 1–2 MÃ Qxxx chọn từ quote_options phù hợp các ý chính; chương trình sẽ ghép nguyên văn nguồn. '
        'Không tự viết lại quote. Tổng toàn bộ chữ trong title+summary+aliases+facts+quotes tối đa 195 từ. '
        'Không nói nguồn không có thông tin khi nguồn thực sự có. Không đưa luật/chính sách của Anh/Mỹ thành luật Việt Nam. '
        'Với trang fruit-and-diabetes, tập trung thẳng câu người tiểu đường có ăn chuối được không: nguồn liệt kê banana '
        'trong các loại trái cây có thể ăn và nhấn mạnh kiểm soát khẩu phần, không suy ra cấm chuối. '
        'Đầu ra phải diễn đạt lại, không dịch dài toàn bộ bài. Chỉ dùng bản thảo có thể kiểm chứng từ trang đã cho.')
    for offset in range(0,len(selected),6):
        batch=selected[offset:offset+6]
        target=CACHE/f'draft-{offset:03d}.json'
        if target.exists():continue
        values=[{k:r[k] for k in ('doc_id','title','url','category')}|{'source_text':r['text'][:14000],
            'quote_options':quote_options(r['text'])} for r in batch]
        result=checked_generation(system,values,batch)
        docs=result['documents']
        if len(docs)!=len(batch):raise ValueError('Missing draft document')
        by_id={r['doc_id']:r for r in batch}
        for doc in docs:validate_draft(doc,by_id[doc['doc_id']])
        dump(target,docs)
        print(json.dumps(dict(drafted=offset+len(batch),total=len(selected))),flush=True)


def review():
    selected=json.loads((CACHE/'selected.json').read_text(encoding='utf-8'))
    drafts=[d for p in sorted(CACHE.glob('draft-*.json')) for d in json.loads(p.read_text(encoding='utf-8'))]
    by_id={d['doc_id']:d for d in drafts}
    if len(by_id)!=126:raise ValueError('Draft corpus incomplete')
    system=('Kiểm tra độc lập tính đúng và mức bám nguồn của từng thẻ y tế tiếng Việt so với nguồn tiếng Anh. '
        'Kiểm tra TẤT CẢ ý trong summary_vi và facts; aliases không được hứa trả lời nội dung không có. '
        'Không tự bổ sung kiến thức; nếu có lỗi, viết lại thẻ chỉ theo nguồn. Giữ đúng doc_id. '
        'Không có liều thuốc, tự chỉnh thuốc, chẩn đoán cá nhân, hứa chữa khỏi. '
        'Summary 35–125 từ cách trắng; tổng title+summary+aliases+facts+support_quotes tối đa 195 từ. '
        'Support_quotes chỉ trả 1–2 MÃ Qxxx lấy từ quote_options; không tự viết lại quote. '
        'Mỗi thẻ có 2–3 facts rất ngắn bằng TIẾNG VIỆT, dạng [thực thể,quan hệ,thực thể], và 3–6 aliases cụ thể. '
        'Bỏ từ tuyệt đối như hoàn toàn, luôn luôn, đảm bảo nếu nguồn chỉ nói có thể hoặc liên quan. '
        'Loại nhận định quá mức, nhầm loại tiểu đường hoặc áp luật Anh/Mỹ cho Việt Nam. '
        'Trả JSON {"documents":[các thẻ đã kiểm tra/sửa],"review":[{"doc_id":"...","changed":true/false,"note":"..."}]} . '
        'Nếu nguồn không đủ cho trọng tâm chọn, chuyển trọng tâm sang khía cạnh thực sự có trong chính trang đó.')
    for offset in range(0,len(selected),6):
        batch=selected[offset:offset+6]
        target=CACHE/f'review-{offset:03d}.json'
        if target.exists():continue
        values=[dict(source_text=r['text'][:18000],quote_options=quote_options(r['text']),draft=by_id[r['doc_id']]) for r in batch]
        result=checked_generation(system,values,batch)
        sources={r['doc_id']:r for r in batch}
        if len(result['documents'])!=len(batch):raise ValueError('Review omitted a document')
        for doc in result['documents']:validate_draft(doc,sources[doc['doc_id']])
        dump(target,result)
        print(json.dumps(dict(reviewed=offset+len(batch),total=len(selected))),flush=True)


def export():
    selected=json.loads((CACHE/'selected.json').read_text(encoding='utf-8'))
    reviews=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(CACHE.glob('review-*.json'))]
    docs=[d for r in reviews for d in r['documents']]
    if len(docs)!=126 or len({d['doc_id'] for d in docs})!=126:raise ValueError('Reviewed corpus incomplete')
    by_id={r['doc_id']:r for r in selected}
    overrides=json.loads((ROOT/'knowledge/diabetes_editorial_overrides.json').read_text(encoding='utf-8'))['documents']
    for doc in docs:
        source=by_id[doc['doc_id']]
        if doc['doc_id'] in overrides:doc.update(overrides[doc['doc_id']])
        doc['support_quotes']=[' '.join(q.split()[:8]) for q in doc['support_quotes']]
        validate_draft(doc,source)
        source_title=source['title'].split(' - Brand')[0].split(' - Common')[0]
        if len(source_title.split())>8:source_title=' '.join(source_title.split()[:8])+'…'
        doc.update(source_url=source['url'],source_title=source_title,category=source['category'],
            source_sha256=source['source_sha256'],retrieved_on=source['retrieved_on'],http_status=200,
            content_type='source_based_vietnamese_paraphrase',review_method='automated_draft_and_independent_source_check')
    dump(ROOT/'knowledge/diabetes_expansion.json',dict(format_version=1,reviewed_on='2026-10-31',
        description='126 additional educational summaries from distinct verified public pages. Automated source checks are not clinical validation.',documents=docs))
    dump(ROOT/'reports/project/corpus_source_review.json',dict(
        documents=len(docs),unique_source_pages=len({d['source_url'] for d in docs}),
        method='Two-pass model-assisted drafting and source checking; exact supporting quotations and metadata validated in code; not clinical validation.',
        editorial_corrections=sorted(overrides),
        review=[dict(doc_id=n['doc_id'],changed=n['changed']) for r in reviews for n in r['review']]))
    print(json.dumps(dict(exported=len(docs))))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['discover','select','draft','review','export'])
    args=parser.parse_args()
    {'discover':discover,'select':select_sources,'draft':draft,'review':review,'export':export}[args.action]()
