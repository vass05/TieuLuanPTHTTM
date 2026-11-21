"""Versioned, read-only Neo4j retrieval for the reviewed diabetes corpus."""

import hashlib
import json
import os
from urllib.parse import urlsplit

from dotenv import dotenv_values

from mvc.models.model_errors import ModelUnavailableError


# Cypher nhận mã tài liệu đã xếp hạng qua tham số. CITES lấy URL và thông tin
# nguồn. evidence_id lưu mã tài liệu chứng minh của từng FACT.
RETRIEVE_CYPHER = """
MATCH (:DiabetesKB {version: $version})
UNWIND $candidates AS candidate
MATCH (d:KBNode:Document {kb_key: $version + '|' + candidate.id})
      -[:CITES]->(s:KBNode:Source)
WHERE s.kb_version = $version
OPTIONAL MATCH (a:KBNode:Alias)-[:RETRIEVES]->(d)
WHERE a.kb_version = $version AND (a.label IN $aliases OR a.label IN candidate.aliases)
WITH candidate, d, s, collect(DISTINCT a.label) AS aliases
OPTIONAL MATCH (:KBNode:Concept)-[f:FACT]->(:KBNode:Concept)
WHERE f.kb_version = $version AND f.evidence_id = d.id
WITH candidate, d, s, aliases,
     collect(DISTINCT CASE WHEN f IS NOT NULL THEN
         {source: f.subject, relation: f.relation, target: f.object, evidence_id: f.evidence_id}
     END) AS graph_paths
RETURN d.id AS doc_id, d.label AS title, d.summary_vi AS content,
       s.id AS source_url, s.label AS publisher, s.source_id AS source_id,
       s.source_group AS source_group, s.source_type AS source_type,
       d.page AS page, d.section AS section, d.content_type AS content_type, aliases, graph_paths
ORDER BY candidate.position
"""

VERSION_CYPHER = """
MATCH (kb:DiabetesKB {version: $version})
RETURN kb.documents AS documents, kb.sources AS sources,
       kb.vietnam AS vietnam, kb.international AS international,
       kb.web AS web, kb.pdf AS pdf
"""


def settings(root):
    """Ưu tiên biến môi trường của tiến trình, sau đó đọc .env cục bộ."""
    local = dotenv_values(root / '.env')
    return {name: os.environ.get(name) or local.get(name) or default
            for name, default in {
                'DIABETES_KB_BACKEND': 'local', 'NEO4J_URI': '',
                'NEO4J_USERNAME': '', 'NEO4J_PASSWORD': '', 'NEO4J_DATABASE': 'neo4j',
            }.items()}


def source_fields(doc):
    url = doc['source_url']
    host = urlsplit(url).hostname or ''
    vietnam = doc.get('source_country') == 'VN' or host.endswith('.vn')
    return dict(source_id='src-' + hashlib.sha256(url.encode()).hexdigest(),
                source_group='vietnam' if vietnam else 'international',
                source_type=doc.get('source_type', 'web'),
                source_title=doc.get('source_title', doc['title']),
                source_language=doc.get('source_language', 'vi' if vietnam else 'en'))


def ordered_graph(dialogue):
    nodes = sorted(dialogue.graph.nodes(data=True), key=lambda row: row[0])
    edges = sorted(dialogue.graph.edges(data=True),
                   key=lambda row: (row[0], row[1], json.dumps(row[2], sort_keys=True)))
    return nodes, edges


def snapshot_version(dialogue):
    """Tính chung mã phiên bản cho trình nhập và backend truy xuất."""
    nodes, edges = ordered_graph(dialogue)
    documents = []
    for doc in sorted(dialogue.documents.values(), key=lambda item: item['doc_id']):
        if doc.get('source_type') == 'pdf' and doc.get('local_path'):
            # Dùng khóa lưu trữ ban đầu của PDF để giữ mã phiên bản khi đổi tên file hiển thị.
            doc_id = doc['doc_id']
            storage_name = 'byt-2558-2022.pdf' if doc_id == 'P01' else f'library/{doc_id.lower()}.pdf'
            doc = dict(doc, local_path=f'sources/pdf/{storage_name}')
        documents.append(doc)
    payload = json.dumps([2, documents, nodes, edges], sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def open_driver(config):
    if not all(config.get(key) for key in ('NEO4J_URI', 'NEO4J_USERNAME', 'NEO4J_PASSWORD')):
        raise ModelUnavailableError('Chưa cấu hình địa chỉ và thông tin đăng nhập Neo4j.')
    try:
        from neo4j import GraphDatabase
        return GraphDatabase.driver(
            config['NEO4J_URI'], auth=(config['NEO4J_USERNAME'], config['NEO4J_PASSWORD']),
            connection_timeout=2, connection_acquisition_timeout=3, max_transaction_retry_time=0,
        )
    except (ImportError, ValueError, TypeError):
        raise ModelUnavailableError('Cấu hình hoặc driver Neo4j chưa sẵn sàng.') from None


class Neo4jKnowledge:
    def __init__(self, config, dialogue):
        self.version = snapshot_version(dialogue)
        self.database = config['NEO4J_DATABASE']
        self.driver = open_driver(config)
        self.docs = dialogue.documents
        self.aliases = dialogue.aliases
        self.facts = {doc_id: set() for doc_id in self.docs}
        for fact in dialogue.facts:
            self.facts[fact[3]].add(fact)

    def _read(self, cypher, **params):
        from neo4j import Query
        from neo4j.exceptions import DriverError, Neo4jError
        try:
            rows, _, _ = self.driver.execute_query(
                Query(cypher, timeout=2), parameters_=dict(version=self.version, **params),
                database_=self.database, routing_='r',
            )
            return [r.data() for r in rows]
        except (DriverError, Neo4jError, OSError):
            raise ModelUnavailableError('Không truy cập được kho tri thức Neo4j.') from None

    def health(self):
        # DiabetesKB đánh dấu phiên bản mà trình nhập đã hoàn tất và đối chiếu.
        rows = self._read(VERSION_CYPHER)
        if len(rows) != 1:
            raise ModelUnavailableError('Phiên bản kho tri thức chưa được nhập vào Neo4j.')
        return rows[0]

    def retrieve(self, candidates, normalized_query):
        """Resolve locally ranked IDs into evidence and graph facts from Neo4j."""
        if not candidates:
            self.health()
            return []
        request = []
        for position, hit in enumerate(candidates):
            doc_id = hit['doc_id']
            aliases = self.aliases.get(doc_id, ())
            matched = [a for a in aliases if f' {a} ' in f' {normalized_query} ']
            request.append(dict(id=doc_id, position=position, aliases=matched))
        rows = self._read(RETRIEVE_CYPHER, candidates=request, aliases=[normalized_query])
        if [row['doc_id'] for row in rows] != [hit['doc_id'] for hit in candidates]:
            raise ModelUnavailableError('Dữ liệu Neo4j thiếu hoặc lệch phiên bản kho tri thức.')

        # Dùng dữ liệu trả về từ Neo4j sau khi đối chiếu nội dung, nguồn,
        # trang PDF và quan hệ với corpus của cùng phiên bản.
        hits = []
        for row, candidate in zip(rows, candidates):
            doc = self.docs[row['doc_id']]
            expected = dict(title=doc['title'], content=doc['summary_vi'],
                            source_url=doc['source_url'], publisher=doc['publisher'],
                            page=doc.get('page'), section=doc.get('section'),
                            content_type=doc.get('content_type'))
            expected.update({key: value for key, value in source_fields(doc).items()
                             if key in ('source_id', 'source_group', 'source_type')})
            if any(row.get(key) != value for key, value in expected.items()):
                raise ModelUnavailableError('Bằng chứng Neo4j không khớp tài liệu đã đối chiếu.')
            facts = {(item['source'], item['relation'], item['target'], item['evidence_id'])
                     for item in row['graph_paths']}
            if facts != self.facts[doc['doc_id']]:
                raise ModelUnavailableError('Quan hệ Neo4j không khớp phiên bản kho tri thức.')
            row.update(score=candidate['score'], match_method=candidate.get('match_method', 'ranked'),
                       backend='neo4j', kb_version=self.version)
            hits.append(row)
        return hits
