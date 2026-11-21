"""Vietnamese query understanding over the exported, source-backed retriever.

The experiment retriever stays frozen. This serving layer expands ordinary
phrasing into topic vocabulary and validates retrieval output before presenting
project-specific, reviewed summaries. It is not an LLM or a clinical reasoner.
"""
import copy
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

SOURCE_PUBLISHERS = {
    'www.niddk.nih.gov': 'NIDDK / NIH',
    'www.cdc.gov': 'CDC',
    'www.medlineplus.gov': 'MedlinePlus / NIH',
    'medlineplus.gov': 'MedlinePlus / NIH',
    'diabetes.org': 'ADA',
    'www.nhs.uk': 'NHS',
    'www.canada.ca': 'Public Health Agency of Canada',
    'www.diabetes.org.uk': 'Diabetes UK',
    'www.nccih.nih.gov': 'NCCIH / NIH',
    'daithaoduong.kcb.vn': 'Cục Quản lý Khám, chữa bệnh – Bộ Y tế',
    'bachmai.gov.vn': 'Bệnh viện Bạch Mai',
    'kcb.vn': 'Cục Quản lý Khám, chữa bệnh – Bộ Y tế',
    'emohbackup.moh.gov.vn': 'Bộ Y tế',
    'bvdaihoc.com.vn': 'Bệnh viện Đại học Y Dược TP.HCM',
    'bvchoray.vn': 'Bệnh viện Chợ Rẫy',
    'benhviennoitiet.vn': 'Bệnh viện Nội tiết Trung ương',
    'tamanhhospital.vn': 'Bệnh viện Đa khoa Tâm Anh',
    'www.vinmec.com': 'Hệ thống Bệnh viện Vinmec',
    'suckhoedoisong.vn': 'Sức khỏe & Đời sống',
    'vjde.vn': 'Tạp chí Nội tiết và Đái tháo đường',
    'tapchinghiencuuyhoc.vn': 'Tạp chí Nghiên cứu Y học',
    'tapchiyhocvietnam.vn': 'Tạp chí Y học Việt Nam',
    'tapchi.ctump.edu.vn': 'Tạp chí Y Dược học Cần Thơ',
    'jcmhch.com.vn': 'Tạp chí Y học lâm sàng Bệnh viện Trung ương Huế',
    'ttyttpbentre.org.vn': 'Bộ Y tế',
    'professional.diabetes.org': 'American Diabetes Association',
    'pmc-oa-opendata.s3.amazonaws.com': 'PubMed Central / NIH',
    'stacks.cdc.gov': 'CDC',
    'shop.diabetes.org.uk': 'Diabetes UK',
}
TRUSTED_HOSTS = set(SOURCE_PUBLISHERS)


def load_extended_documents(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format_version') != 1:
        raise ValueError('Invalid extended corpus')
    documents = data['documents']
    seen = set()
    for doc in documents:
        url = urlparse(doc['source_url'])
        if (url.scheme != 'https' or url.hostname not in TRUSTED_HOSTS or url.username or url.password
                or doc['doc_id'] in seen):
            raise ValueError('Invalid knowledge source or duplicate document')
        if not doc.get('summary_vi') or not doc.get('aliases') or not doc.get('facts'):
            raise ValueError('Incomplete knowledge document')
        if doc.get('source_type', 'web') not in ('web', 'pdf'):
            raise ValueError('Invalid knowledge source type')
        if doc.get('source_type') == 'pdf':
            page = doc.get('page')
            if type(page) is not int or page < 1 or not doc.get('section'):
                raise ValueError('Missing PDF evidence location')
        seen.add(doc['doc_id'])
        doc.update(publisher=SOURCE_PUBLISHERS[url.hostname],
            reviewed_on=doc.get('reviewed_on', data['reviewed_on']),
            content_type=doc.get('content_type','manually_reviewed_vietnamese_paraphrase'),
            section=doc.get('section', doc['title']))
    return documents


# Specific phrases, matched on word boundaries. A bare 'an' would also match
# unrelated language, so we require a food/question phrase instead.
TOPICS = (
    ('nutrition', ('an duoc gi','an duoc','nen an gi','nen an','an gi','kieng gi','kieng an','nen kieng',
        'co duoc an','duoc an','an uong','che do an','thuc don','dinh duong','bua an',
        'khau phan','thuc pham','hoa qua','trai cay','an com','an banh','mon gi',
        'uong gi','nuoc ngot','sua gi'),
        'dinh duong bua an thuc pham khau phan do uong', ('D05',)),
    ('activity', ('nen tap gi','tap gi','tap luyen','the duc','di bo','van dong','hoat dong the chat'),
        'van dong hoat dong the chat tap luyen', ('D06',)),
    ('symptoms', ('dau hieu','trieu chung','bieu hien','khat nuoc','khat nhieu','tieu nhieu','nhin mo','cham lanh'),
        'trieu chung bieu hien khat nhieu tieu nhieu', ('D02',)),
    ('a1c', ('hba1c','a1c','ba thang'),
        'a1c hba1c ba thang ke hoach cham soc', ('D04',)),
    ('tests', ('xet nghiem','tam soat','chan doan','kiem tra tieu duong','dung nap glucose','glucose luc doi',
        'co bi tieu duong','co mac tieu duong','co phai tieu duong','lieu co bi'),
        'xet nghiem chan doan glucose luc doi dung nap glucose', ('D03',)),
    ('kidney', ('suy than','benh than','chuc nang than','kiem tra than','egfr','gfr','albumin','loc cau than'),
        'than gfr albumin nuoc tieu muc loc cau than', ('D09',)),
    ('prevention', ('phong ngua','phong tranh','ngan ngua','tri hoan','giam nguy co'),
        'phong ngua tri hoan tieu duong nguy co can nang', ('D07',)),
    ('hypoglycemia', ('ha duong huyet','glucose thap','duong huyet thap','run tay'),
        'ha duong huyet glucose thap run tay chong mat', ('D08',)),
    ('medicines', ('thuoc','insulin','metformin','tac dung phu'),
        'thuoc insulin dieu tri tac dung phu doi ngu y te', ('D10',)),
    ('overview', ('tieu duong la gi','dai thao duong la gi','khai niem tieu duong'),
        'tieu duong la gi insulin glucose khai niem', ('D01',)),
)

# A few questions need several terms to be interpreted together. Matching the
# individual terms can otherwise pick a general document or an incidental alias.
QUERY_PATTERNS = (
    ('type1', (('tuyp 1',), ('tuyp 2',), ('khac nhau', 'phan biet', 'so sanh')), ('K02',)),
    ('cgm', (('cgm', 'cam bien'), ('may do', 'dau ngon tay'), ('khac nhau', 'phan biet', 'so sanh')), ('K14',)),
    ('hypoglycemia', (('bo y te',), ('ha duong huyet', 'duong huyet thap')), ('V05',)),
    ('activity', (('bo y te',), ('van dong', 'tap luyen'), ('phong', 'phong ngua')), ('V04',)),
    ('children_type_2_diabetes', (('tre em', 'tre nho'), ('tuyp 2',), ('co the mac', 'co bi', 'co mac')), ('K133',)),
    ('older_adults', (('nguoi lon tuoi', 'nguoi cao tuoi'), ('tieu duong', 'dai thao duong'),
                      ('can chu y gi', 'nen luu y gi')), ('S8A4EF61148', 'S4E76D30AFD')),
)


def normalize_question(text):
    text = unicodedata.normalize('NFD',str(text).lower().replace('đ','d'))
    text = ''.join(c for c in text if unicodedata.category(c)!='Mn')
    text = re.sub(r'[^a-z0-9]+',' ',text).strip()
    text = re.sub(r'\b(?:tuyp|typ|tip|type|loai)\s*(?:ii|2)\b','tuyp 2',text)
    return re.sub(r'\b(?:tuyp|typ|tip|type|loai)\s*(?:i|1)\b','tuyp 1',text)


def load_conversation_documents(documents, path):
    """Merge reviewed project text without changing experiment documents/index."""
    result = copy.deepcopy(documents)
    by_id = {d['doc_id']:d for d in result}
    path = Path(path)
    if not path.exists():
        return result
    overlay = json.loads(path.read_text(encoding='utf-8'))
    if overlay.get('format_version')!=1:
        raise ValueError('Unsupported conversation document format')
    for update in overlay['documents']:
        original = by_id.get(update['doc_id'])
        if original is None or original['source_url']!=update['source_url']:
            raise ValueError('Conversation source does not match the verified corpus')
        if not isinstance(update['summary_vi'],str) or not update['summary_vi'].strip():
            raise ValueError('Missing reviewed summary')
        original.update(update)
    return result


class DiabetesDialogue:
    def __init__(self, retriever, documents, extended=None, supplemental=None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.retriever = retriever
        self.documents = {d['doc_id']:d for d in documents}
        self.extended = extended or []
        self.supplemental = supplemental or []
        self.supplemental_ids = {doc['doc_id'] for doc in self.supplemental}
        serving_documents = self.extended + self.supplemental
        reserved={normalize_question(a) for d in documents if not d.get('review_method') for a in d.get('aliases',[])}
        reserved.update(phrase for _,phrases,_,_ in TOPICS for phrase in phrases)
        self.aliases={}
        for doc in serving_documents:
            aliases=[]
            for value in doc['aliases']:
                alias=normalize_question(value)
                if doc.get('review_method'):
                    alias=re.sub(r'^(?:nguoi |benh nhan )?(?:tieu duong|dai thao duong)(?: tuyp [12])?\s+','',alias)
                    alias=re.sub(r'\s+(?:khi|cho)(?: nguoi| benh nhan)?(?: bi| mac)? (?:tieu duong|dai thao duong)(?: tuyp [12])?$','',alias)
                    alias=re.sub(r'\s+(?:duoc khong|la gi|nhu the nao)$','',alias)
                    if alias in reserved:continue
                if alias and alias not in aliases:aliases.append(alias)
            if doc.get('review_method'):
                parts=urlparse(doc['source_url']).path.strip('/').split('/')
                if len(parts)>=2 and parts[0]=='medicines' and parts[1] not in {'insulin','metformin'}:
                    # A verified medicine page must answer a question containing
                    # its generic name even when the sentence differs from aliases.
                    generic=parts[1].replace('-',' ')
                    if generic not in aliases:aliases.append(generic)
            self.aliases[doc['doc_id']]=aliases
        self.alias_patterns={did:[(a,re.compile(r'\b'+re.escape(a)+r'\b')) for a in aliases]
            for did,aliases in self.aliases.items()}
        self.lexical = TfidfVectorizer(preprocessor=normalize_question, ngram_range=(1,2), sublinear_tf=True)
        self.characters = TfidfVectorizer(preprocessor=normalize_question, analyzer='char_wb', ngram_range=(3,5))
        if self.extended:
            texts = [' '.join(d['aliases'])+' '+d['title']+' '+d['summary_vi'] for d in self.extended]
            self.lexical_matrix = self.lexical.fit_transform(texts)
            self.character_matrix = self.characters.fit_transform(texts)
        if self.supplemental:
            titles = [doc['title'] + ' ' + ' '.join(doc['aliases']) for doc in self.supplemental]
            self.supplemental_index = TfidfVectorizer(preprocessor=normalize_question, ngram_range=(1, 2))
            self.supplemental_matrix = self.supplemental_index.fit_transform(titles)
        import networkx as nx
        self.graph = nx.MultiDiGraph()
        self.facts = list(retriever.facts)
        for doc in serving_documents:
            self.facts.extend((s,r,o,doc['doc_id']) for s,r,o in doc['facts'])
        for doc in self.documents.values():
            did = doc['doc_id']
            self.graph.add_node(did, kind='document', label=doc['title'])
            self.graph.add_node(doc['source_url'], kind='source', label=doc['publisher'])
            self.graph.add_edge(did, doc['source_url'], relation='cites', evidence_id=did)
            for alias in self.aliases.get(did,{normalize_question(a) for a in doc.get('aliases',[])}):
                aid = 'alias:'+alias
                self.graph.add_node(aid, kind='alias', label=alias)
                self.graph.add_edge(aid, did, relation='retrieves', evidence_id=did)
            for subject, relation, obj, evidence_id in self.facts:
                if evidence_id != did:
                    continue
                for label in (subject,obj):
                    self.graph.add_node('concept:'+normalize_question(label),kind='concept',label=label)
                self.graph.add_edge('concept:'+normalize_question(subject), 'concept:'+normalize_question(obj),
                    relation=relation, evidence_id=did, subject=subject, object=obj)

    def statistics(self):
        kinds = [data['kind'] for _,data in self.graph.nodes(data=True)]
        return dict(nodes=self.graph.number_of_nodes(), relations=self.graph.number_of_edges(),
            clinical_entities=kinds.count('concept'), clinical_relations=len(self.facts),
            aliases=kinds.count('alias'), documents=len(self.documents),
            sources=len({d['source_url'] for d in self.documents.values()}))

    def understand(self, query):
        text = normalize_question(query)
        named_sources = [doc for doc in self.supplemental
                         if text in self.aliases[doc['doc_id']]
                         and (doc.get('source_type') == 'pdf' or text.startswith('nguon ')
                              or doc.get('review_method') == 'manual_source_comparison')]
        if named_sources:
            return dict(topics=list(dict.fromkeys(doc['topic'] for doc in named_sources)),
                        expanded_query=query, preferred_doc_ids=[doc['doc_id'] for doc in named_sources],
                        match_method='named_source')
        bounded = f' {text} '
        for topic, phrase_groups, doc_ids in QUERY_PATTERNS:
            if (all(doc_id in self.documents for doc_id in doc_ids)
                    and all(any(f' {phrase} ' in bounded for phrase in group) for group in phrase_groups)):
                return dict(topics=[topic], expanded_query=query, preferred_doc_ids=list(doc_ids),
                            match_method='combined_phrases')
        matched = []
        for name,phrases,expansion,doc_ids in TOPICS:
            if any(re.search(r'\b'+re.escape(phrase)+r'\b',text) for phrase in phrases):
                matched.append((name,expansion,doc_ids))
        specific = []
        for doc in self.extended:
            spans = [(m.start(),m.end()) for a,pattern in self.alias_patterns[doc['doc_id']]
                for m in pattern.finditer(text)
                if self.graph.has_edge('alias:'+a,doc['doc_id'])]
            if spans:
                specific.append((spans,doc))
        if specific:
            # Suppress a generic substring ("cam") when a specific entity
            # ("nuoc cam") occupies the same span, but keep independent topics.
            all_spans = [span for spans,_ in specific for span in spans]
            specific = [(spans,d) for spans,d in specific if any(not any(
                a<=start and end<=b and (a,b)!=(start,end) for a,b in all_spans) for start,end in spans)]
            background = {'type1','type2','prediabetes','pregnancy'}
            focused=[item for item in specific if item[1]['topic'] not in background]
            if focused:specific=focused
            def relevance(item):
                spans,doc=item
                title=normalize_question(doc['title'])
                title_match=max((b-a for a,b in spans if text[a:b] in title),default=0)
                return (doc['topic'] in background,-max(b-a for a,b in spans),-title_match)
            specific.sort(key=relevance)
            scores=self._context_scores(query)
            if len(scores):
                best=max(range(len(scores)),key=lambda i:scores[i])
                best_doc=self.extended[best]
                matched_ids={doc['doc_id'] for _,doc in specific}
                best_matched=max((scores[i] for i,doc in enumerate(self.extended) if doc['doc_id'] in matched_ids),default=0)
                generic={'tieu','duong','huyet','benh','va','cua','cho','co','gi','lam','the','nao','huong','tuyp'}
                title_terms=set(normalize_question(best_doc['title']).split())-generic
                focus_overlap=len(title_terms & (set(text.split())-generic))
                if (best_doc['doc_id'] not in matched_ids and not re.search(r'\d',text) and focus_overlap>=2
                    and scores[best]>=.28 and scores[best]>1.4*best_matched):
                    return dict(topics=[best_doc['topic']],expanded_query=query,
                        preferred_doc_ids=[best_doc['doc_id']],match_method='lexical_context',
                        rank_scores={best_doc['doc_id']:float(scores[best])})
            chosen = [d for _,d in specific][:3]
            return dict(topics=list(dict.fromkeys(d['topic'] for d in chosen)),
                expanded_query=query,preferred_doc_ids=[d['doc_id'] for d in chosen])
        return dict(topics=[m[0] for m in matched],
            expanded_query=' '.join(m[1] for m in matched) if matched else query,
            preferred_doc_ids=list(dict.fromkeys(doc_id for m in matched for doc_id in m[2])))

    def _reviewed_hit(self, hit):
        original = self.retriever.by_id.get(hit.get('doc_id'))
        if original is None or hit.get('content')!=original['summary_vi'] or hit.get('source_url')!=original['source_url']:
            raise ValueError('Retrieved evidence was not verified')
        result = copy.deepcopy(hit)
        result['content'] = self.documents[hit['doc_id']]['summary_vi']
        return result

    def search(self, query, k=3, method='Hybrid', understanding=None):
        intent = understanding or self.understand(query)
        raw = self.retriever.search(query,k=k,method=method)
        # Validate even candidates that a later ranking step may discard.
        candidates = {hit['doc_id']:self._reviewed_hit(hit) for hit in raw}
        preferred = set(intent['preferred_doc_ids'])
        if preferred & self.supplemental_ids:
            return [self._extended_hit(self.documents[did], 1.0, intent.get('match_method', 'named_source'))
                    for did in intent['preferred_doc_ids'] if did in self.supplemental_ids][:k]
        text = normalize_question(query)
        for prefix in ('pdf ', 'nguon pdf '):
            if text.startswith(prefix):
                return self._search_supplemental(text[len(prefix):], k, pdf_only=True) if self.supplemental else []
        extra_ids = {d['doc_id'] for d in self.extended}
        if preferred & extra_ids:
            return [self._extended_hit(self.documents[did],intent.get('rank_scores',{}).get(did,1.0),
                intent.get('match_method','graph_alias')) for did in intent['preferred_doc_ids'] if did in extra_ids][:k]
        if preferred:
            expanded = self.retriever.search(intent['expanded_query'],k=k,method=method)
            for hit in expanded:
                reviewed = self._reviewed_hit(hit)
                if hit['doc_id'] in preferred:
                    reviewed['match_method'] = 'topic_expansion'
                    candidates[hit['doc_id']] = reviewed
            # Only report material relevant to an understood topic. Do not
            # lower thresholds or fabricate a hit if the lookup still fails.
            candidates = {key:hit for key,hit in candidates.items() if key in preferred}
        ranked = sorted(candidates.values(),key=lambda hit:(-hit['score'],hit['doc_id']))
        if not ranked and not preferred and self.extended:
            # Remove generic disease/question wording before comparing. A bare
            # mention of diabetes must not retrieve an arbitrary medical page.
            text = normalize_question(query)
            for phrase in ('dai thao duong','tieu duong','cho toi','cho minh','duoc khong','la gi'):
                text = text.replace(phrase,' ')
            words = [w for w in text.split() if w not in {'co','bi','benh','toi','minh','hoi','ve','thi','va','hay','khong','nhu','the','nao','gi','a','oi','lam','sao'}]
            if words:
                clean = ' '.join(words)
                lexical = (self.lexical_matrix @ self.lexical.transform([clean]).T).toarray().ravel()
                chars = (self.character_matrix @ self.characters.transform([clean]).T).toarray().ravel()
                scores = .65*lexical+.35*chars
                indices = sorted(range(len(scores)),key=lambda i:-scores[i])
                ranked = [self._extended_hit(self.extended[i],float(scores[i]),'lexical_character')
                    for i in indices[:k] if scores[i]>=.23 and scores[i]>=scores[indices[0]]*.75]
        if not ranked and self.supplemental:
            ranked = self._search_supplemental(query, k)
        return ranked[:k]

    def _search_supplemental(self, query, k, pdf_only=False):
        text = normalize_question(query)
        generic = {'dai', 'thao', 'duong', 'tieu', 'benh', 'nguoi', 'co', 'mac', 'bi', 'la',
                   'cach', 'bao', 'nhieu', 'gi', 'khi', 'cho', 'lam', 'nen', 'nhu', 'the',
                   'nao', 'tai', 'doi', 'voi', 'va', 'trong', 'cua', 'khong', 'duoc'}
        terms = set(text.split()) - generic
        if len(terms) < 2:
            return []
        scores = (self.supplemental_matrix @ self.supplemental_index.transform([text]).T).toarray().ravel()
        hits = []
        for i in sorted(range(len(scores)), key=lambda idx: -scores[idx]):
            if scores[i] < .38 or len(hits) >= k:
                break
            doc = self.supplemental[i]
            if pdf_only and doc.get('source_type') != 'pdf':
                continue
            title = set(normalize_question(doc['title']).split()) - generic
            if len(terms & title) >= 2:
                hits.append(self._extended_hit(doc, float(scores[i]), 'supplemental_title'))
        return hits

    def _extended_hit(self, doc, score, method):
        return dict(doc_id=doc['doc_id'],title=doc['title'],source_url=doc['source_url'],
            publisher=doc['publisher'],content=doc['summary_vi'],score=score,match_method=method,
            graph_paths=[dict(source=s,relation=r,target=o,evidence_id=doc['doc_id']) for s,r,o in doc['facts']])

    def _context_scores(self,query):
        if not self.extended:return []
        text=normalize_question(query)
        for phrase in ('dai thao duong','tieu duong','cho toi','cho minh','duoc khong','la gi'):
            text=text.replace(phrase,' ')
        words=[w for w in text.split() if w not in {'co','bi','benh','toi','minh','hoi','ve','thi','va','hay','khong',
            'nhu','the','nao','gi','a','oi','lam','sao','vi','luc'}]
        if not words:return []
        clean=' '.join(words)
        lexical=(self.lexical_matrix@self.lexical.transform([clean]).T).toarray().ravel()
        chars=(self.character_matrix@self.characters.transform([clean]).T).toarray().ravel()
        return .65*lexical+.35*chars
