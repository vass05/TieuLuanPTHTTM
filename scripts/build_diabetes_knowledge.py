"""Export the serving graph and its transparent counts for project review."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mvc.models.agents_model import AgentsModel
import networkx as nx


def main():
    model=AgentsModel(ROOT,ROOT/'instance/knowledge_check.sqlite3',external_enabled=False)
    model.ensure_loaded()
    out=ROOT/'reports/project'
    out.mkdir(parents=True,exist_ok=True)
    (out/'knowledge_graph.json').write_text(json.dumps(nx.node_link_data(model.dialogue.graph),
        ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(statistics=model.dialogue.statistics(),
        note='Nodes include distinct concepts, query aliases, source pages and documents; aliases are not clinical entities.',
        documents=[{k:d[k] for k in ('doc_id','title','publisher','source_url','reviewed_on')} for d in model.documents])
    (out/'knowledge_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report['statistics']))


if __name__=='__main__':main()
