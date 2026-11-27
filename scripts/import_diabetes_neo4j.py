"""Export the active corpus to Cypher and optionally import it into Neo4j."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mvc.models.agents_model import AgentsModel
from mvc.models.model_errors import ModelUnavailableError
from mvc.models.neo4j_knowledge import open_driver, ordered_graph, settings, snapshot_version, source_fields


CONSTRAINTS = (
    'CREATE CONSTRAINT diabetes_kb_node IF NOT EXISTS FOR (n:KBNode) REQUIRE n.kb_key IS UNIQUE',
    'CREATE CONSTRAINT diabetes_kb_version IF NOT EXISTS FOR (k:DiabetesKB) REQUIRE k.version IS UNIQUE',
)
LABELS = dict(document='Document', source='Source', alias='Alias', concept='Concept')
PUBLISH = 'MERGE (k:DiabetesKB {version: $version}) SET k += $counts'
AUDIT = """
MATCH (n:KBNode {kb_version: $version})
RETURN n.kind AS kind, count(*) AS total
"""
AUDIT_EDGES = """
MATCH (n:KBNode)-[r]->(m:KBNode)
WHERE n.kb_version = $version AND m.kb_version = $version AND r.kb_version = $version
RETURN type(r) AS kind, count(*) AS total
"""
REQUIRED_SPLIT = {
    ('vietnam', 'web'): 199,
    ('vietnam', 'pdf'): 100,
    ('international', 'web'): 200,
    ('international', 'pdf'): 100,
}


def literal(value):
    if isinstance(value, dict):
        return '{' + ', '.join(f'`{key}`: {literal(item)}' for key, item in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ',\n'.join(map(literal, value)) + ']'
    return json.dumps(value, ensure_ascii=False)


def batches(query, rows, batch_size=100):
    for start in range(0, len(rows), batch_size):
        yield query, {'rows': rows[start:start + batch_size]}


def payload(dialogue):
    """Chuẩn bị danh mục nguồn, lô ghi và số liệu dùng để kiểm tra khi import."""
    version = snapshot_version(dialogue)
    nodes, edges = ordered_graph(dialogue)
    documents = dialogue.documents
    catalog = {}
    # Một URL gốc có thể chứng minh nhiều đoạn. Danh mục đếm URL riêng biệt.
    for doc in sorted(documents.values(), key=lambda item: item['doc_id']):
        url = doc['source_url']
        fields = source_fields(doc)
        source = catalog.setdefault(url, dict(**fields, source_url=url, publisher=doc['publisher'], documents=[]))
        evidence = {k: doc[k] for k in ('doc_id', 'title', 'topic', 'category', 'content_type', 'section', 'page', 'reviewed_on',
                    'published_on', 'source_sha256', 'local_path', 'support_quotes', 'review_method', 'original_url',
                    'doi', 'page_count', 'source_bytes') if k in doc}
        source['documents'].append(evidence)

    statements = []
    for kind, label in LABELS.items():
        rows = []
        for node_id, data in nodes:
            if data['kind'] != kind:
                continue
            properties = dict(data, id=node_id, kb_version=version)
            if kind == 'source':
                properties.update({k: v for k, v in catalog[node_id].items() if k != 'documents'})
            if kind == 'document':
                doc = documents[node_id]
                properties.update({k: doc[k] for k in ('summary_vi', 'page', 'section', 'topic', 'category', 'content_type',
                                  'reviewed_on', 'source_sha256', 'support_quotes') if k in doc})
            # Khóa MERGE tách các phiên bản và ổn định khi nhập lại cùng phiên bản.
            rows.append(dict(key=f'{version}|{node_id}', properties=properties))
        query = (f'UNWIND $rows AS row MERGE (n:KBNode:{label} {{kb_key: row.key}}) '
                 'SET n += row.properties')
        statements.extend(batches(query, rows))

    relationships = {'CITES': [], 'RETRIEVES': [], 'FACT': []}
    occurrences = Counter()
    # Hai khái niệm có thể có nhiều cạnh. Mã cạnh giữ cả nội dung và xuất xứ.
    for start, end, data in edges:
        relation = data['relation']
        kind = relation.upper() if relation in ('cites', 'retrieves') else 'FACT'
        content = json.dumps([start, end, data], ensure_ascii=False, sort_keys=True)
        occurrences[content] += 1
        edge_id = hashlib.sha256(f'{version}|{content}|{occurrences[content]}'.encode()).hexdigest()
        relationships[kind].append(dict(start=f'{version}|{start}', end=f'{version}|{end}',
                                       key=edge_id, properties=dict(data, kb_version=version)))
    for kind, rows in relationships.items():
        query = ('UNWIND $rows AS row MATCH (a:KBNode {kb_key: row.start}), (b:KBNode {kb_key: row.end}) '
                 f'MERGE (a)-[r:{kind} {{kb_edge_id: row.key}}]->(b) SET r += row.properties')
        statements.extend(batches(query, rows))

    groups = Counter(item['source_group'] for item in catalog.values())
    types = Counter(item['source_type'] for item in catalog.values())
    counts = dict(documents=len(documents), sources=len(catalog), vietnam=groups['vietnam'],
                  international=groups['international'], web=types['web'], pdf=types['pdf'])
    node_counts = dict(Counter(data['kind'] for _, data in nodes))
    edge_counts = {key: len(value) for key, value in relationships.items()}
    manifest = dict(kb_version=version, counts=counts, sources=list(catalog.values()))
    return version, counts, manifest, statements, node_counts, edge_counts


def write_export(out, version, counts, catalog, statements):
    """Ghi file Cypher để chạy thủ công và danh mục nguồn để tra cứu bằng chứng."""
    cypher = ['// Reviewed diabetes graph. Rebuild with scripts/import_diabetes_neo4j.py.',
              '// Thứ tự nhập: tạo ràng buộc, ghi nút, ghi quan hệ, ghi thống kê phiên bản.',
              '// CITES: tài liệu → nguồn. RETRIEVES: bí danh → tài liệu.',
              '// FACT: khái niệm → khái niệm, có evidence_id trỏ về mã tài liệu.',
              f'// KB version: {version}', *(f'{query};' for query in CONSTRAINTS)]
    for query, params in statements:
        cypher.append(query.replace('$rows', literal(params['rows'])) + ';')
    cypher.append(PUBLISH.replace('$version', literal(version)).replace('$counts', literal(counts)) + ';')
    (out / 'DB_diabet.cypher').write_text('\n\n'.join(cypher) + '\n', encoding='utf-8')
    catalog_dir = out / 'sources'
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n',
                                            encoding='utf-8')


def import_into_database(config, version, counts, statements, node_counts, edge_counts):
    # Ghi dữ liệu, kiểm tra số lượng và đánh dấu phiên bản trong cùng transaction.
    def write(tx):
        for cypher, params in statements:
            tx.run(cypher, params).consume()
        actual_nodes = {row['kind']: row['total'] for row in tx.run(AUDIT, version=version)}
        actual_edges = {row['kind']: row['total'] for row in tx.run(AUDIT_EDGES, version=version)}
        if actual_nodes != node_counts or actual_edges != {k: v for k, v in edge_counts.items() if v}:
            raise ValueError('Neo4j counts do not match the corpus. Import transaction rolled back.')
        tx.run(PUBLISH, version=version, counts=counts).consume()

    with open_driver(config) as driver:
        with driver.session(database=config['NEO4J_DATABASE']) as session:
            for query in CONSTRAINTS:
                session.run(query).consume()
            session.execute_write(write)


def main():
    # Mặc định chỉ xuất tệp. Cờ --import mới ghi dữ liệu vào Neo4j.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import', dest='import_db', action='store_true', help='also import to Neo4j from .env')
    parser.add_argument('--require-complete', action='store_true', help='require 399 web sources and 200 PDFs, 100 PDFs per group')
    args = parser.parse_args()
    model = AgentsModel(ROOT, ROOT / 'instance' / 'kb_export.sqlite3',
                        external_enabled=False, knowledge_backend='local')
    model.ensure_loaded()
    version, counts, catalog, statements, nodes, edges = payload(model.dialogue)
    if args.require_complete:
        split = Counter((row['source_group'], row['source_type']) for row in catalog['sources'])
        if split != REQUIRED_SPLIT:
            parser.error(f'Expected 399 web sources and 200 PDFs with the required split. Found {dict(split)}.')
        pdf_evidence = [source['documents'][0] for source in catalog['sources'] if source['source_type'] == 'pdf']
        if (any(not item.get('source_sha256') or not item.get('support_quotes') or not item.get('page')
                for item in pdf_evidence)
                or len({item['source_sha256'] for item in pdf_evidence}) != counts['pdf']):
            parser.error('Every PDF must have a distinct fingerprint and page-backed evidence.')
        if any(not doc.get('summary_vi') or not doc.get('source_url') for doc in model.documents):
            parser.error('At least one document is missing its evidence or source URL.')
        if any(not model.dialogue.graph.has_edge(doc['doc_id'], doc['source_url'])
               for doc in model.documents):
            parser.error('At least one document is missing its CITES relationship.')
    write_export(ROOT / 'knowledge', version, counts, catalog, statements)
    if args.import_db:
        try:
            from neo4j.exceptions import DriverError, Neo4jError
        except ImportError:
            parser.exit(1, 'Install the Neo4j driver from requirements.txt before importing.\n')
        try:
            import_into_database(settings(ROOT), version, counts, statements, nodes, edges)
        except ModelUnavailableError as exc:
            parser.exit(1, f'{exc}\n')
        except (DriverError, Neo4jError, OSError) as exc:
            parser.exit(1, f'Neo4j import failed ({type(exc).__name__}). Check database settings.\n')
    print(json.dumps(dict(kb_version=version, imported=args.import_db, **counts), ensure_ascii=False))


if __name__ == '__main__':
    main()
