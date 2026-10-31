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

TRUSTED_HOSTS = {'www.niddk.nih.gov', 'www.cdc.gov', 'www.medlineplus.gov', 'medlineplus.gov', 'diabetes.org', 'www.nhs.uk', 'www.canada.ca'}


def load_extended_documents(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format_version') != 1:
        raise ValueError('Invalid extended corpus')
    documents = data['documents']
    seen = set()
    for doc in documents:
        url = urlparse(doc['source_url'])
        if url.scheme != 'https' or url.hostname not in TRUSTED_HOSTS or doc['doc_id'] in seen:
            raise ValueError('Invalid knowledge source or duplicate document')
        if not doc.get('summary_vi') or not doc.get('aliases') or not doc.get('facts'):
            raise ValueError('Incomplete knowledge document')
        seen.add(doc['doc_id'])
        doc.update(publisher=('CDC' if 'cdc.gov' in url.hostname else 'ADA' if url.hostname == 'diabetes.org'
            else 'MedlinePlus / NIH' if 'medlineplus' in url.hostname else 'NHS' if url.hostname=='www.nhs.uk'
            else 'Public Health Agency of Canada' if url.hostname=='www.canada.ca' else 'NIDDK / NIH'),
            reviewed_on=data['reviewed_on'], content_type='manually_reviewed_vietnamese_paraphrase', section=doc['title'])
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
    def __init__(self, retriever, documents, extended=None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.retriever = retriever
        self.documents = {d['doc_id']:d for d in documents}
        self.extended = extended or []
        self.aliases = {d['doc_id']:[normalize_question(a) for a in d['aliases']] for d in self.extended}
        self.lexical = TfidfVectorizer(preprocessor=normalize_question, ngram_range=(1,2), sublinear_tf=True)
        self.characters = TfidfVectorizer(preprocessor=normalize_question, analyzer='char_wb', ngram_range=(3,5))
        if self.extended:
            texts = [' '.join(d['aliases'])+' '+d['title']+' '+d['summary_vi'] for d in self.extended]
            self.lexical_matrix = self.lexical.fit_transform(texts)
            self.character_matrix = self.characters.fit_transform(texts)
        import networkx as nx
        self.graph = nx.MultiDiGraph()
        self.facts = list(retriever.facts)
        for doc in self.extended:
            self.facts.extend((s,r,o,doc['doc_id']) for s,r,o in doc['facts'])
        for doc in self.documents.values():
            did = doc['doc_id']
            self.graph.add_node(did, kind='document', label=doc['title'])
            self.graph.add_node(doc['source_url'], kind='source', label=doc['publisher'])
            self.graph.add_edge(did, doc['source_url'], relation='cites', evidence_id=did)
            for alias in {normalize_question(a) for a in doc.get('aliases',[])}:
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
        matched = []
        for name,phrases,expansion,doc_ids in TOPICS:
            if any(re.search(r'\b'+re.escape(phrase)+r'\b',text) for phrase in phrases):
                matched.append((name,expansion,doc_ids))
        specific = []
        for doc in self.extended:
            spans = [(m.start(),m.end()) for a in self.aliases[doc['doc_id']]
                for m in re.finditer(r'\b'+re.escape(a)+r'\b',text)
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
            specific.sort(key=lambda item:(item[1]['topic'] in background,-max(b-a for a,b in item[0])))
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
        extra_ids = {d['doc_id'] for d in self.extended}
        if preferred & extra_ids:
            return [self._extended_hit(self.documents[did],1.0,'graph_alias') for did in intent['preferred_doc_ids'] if did in extra_ids][:k]
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
        return ranked[:k]

    def _extended_hit(self, doc, score, method):
        return dict(doc_id=doc['doc_id'],title=doc['title'],source_url=doc['source_url'],
            publisher=doc['publisher'],content=doc['summary_vi'],score=score,match_method=method,
            graph_paths=[dict(source=s,relation=r,target=o,evidence_id=doc['doc_id']) for s,r,o in doc['facts']])
