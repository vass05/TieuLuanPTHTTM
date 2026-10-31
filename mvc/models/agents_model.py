"""Serving-only Chapter 6 runtime: notebook artifacts, bounded workflows and task memory."""
import copy
import json
import logging
import math
import threading
import time
import uuid
from pathlib import Path

from mvc.models.agent_store import AgentStore, utc_now
from mvc.models.artifact_utils import artifact_digest
from mvc.models.model_errors import ModelUnavailableError, TaskConflictError
from mvc.models.assistant_synthesis import AssistantSynthesis
from mvc.models.prediction_dialogue import prediction_request, prediction_reply, prediction_followup
from mvc.models.diabetes_dialogue import DiabetesDialogue, load_conversation_documents, load_extended_documents, normalize_question

LOGGER = logging.getLogger(__name__)

FEATURE_FIELDS = [
    ('Pregnancies', 'Số lần mang thai', 'lần', 'count', '1'),
    ('Glucose', 'Glucose sau 2 giờ OGTT', 'mg/dL', 'mg/dL', 'any'),
    ('BloodPressure', 'Huyết áp tâm trương', 'mmHg', 'mmHg', 'any'),
    ('SkinThickness', 'Độ dày nếp gấp da', 'mm', 'mm', 'any'),
    ('Insulin', 'Insulin huyết thanh sau 2 giờ', 'µU/mL', 'uU/mL', 'any'),
    ('BMI', 'Chỉ số khối cơ thể (BMI)', 'kg/m²', 'kg/m2', 'any'),
    ('DiabetesPedigreeFunction', 'Chỉ số phả hệ tiểu đường', 'điểm', 'score', 'any'),
    ('Age', 'Tuổi', 'năm', 'years', '1'),
]


class AgentsModel:
    def __init__(self, root, database_path, external_enabled=None):
        self.root = Path(root)
        self.store = AgentStore(database_path)
        self._lock = threading.RLock()
        self._loaded = False
        self.synthesis = AssistantSynthesis(self.root,external_enabled)

    def ensure_loaded(self):
        with self._lock:
            if self._loaded:
                return
            try:
                import joblib
                import networkx as nx
                import numpy as np
                import sklearn
                import torch
                from mvc.models import chapter6_core as core

                model_root = self.root / 'model'
                agents = model_root / 'agents'
                manifest = json.loads((agents / 'manifest.json').read_text(encoding='utf-8'))
                if manifest.get('digest_format') != 'normalized-text-v1':
                    raise ModelUnavailableError('Cần đóng gói lại artifact bằng scripts/export_chapter6_project.py.')
                if sklearn.__version__ != manifest['packages']['scikit-learn']:
                    raise ModelUnavailableError('Phiên bản scikit-learn khác môi trường xuất mô hình. Cài requirements.txt.')
                for relative, expected in manifest['files'].items():
                    path = (model_root / relative).resolve()
                    if not path.is_relative_to(model_root.resolve()):
                        raise ValueError('Invalid artifact path')
                    if artifact_digest(path) != expected:
                        raise ModelUnavailableError('Artifact đã thay đổi. Chạy lại scripts/export_chapter6_project.py.')
                core_file = Path(core.__file__)
                if artifact_digest(core_file) != manifest['inference_core_sha256']:
                    raise ModelUnavailableError('Mã suy luận khác bản xuất notebook. Chạy lại script export.')
                self.metadata = json.loads((model_root / 'diabetes/pima_model_metadata.json').read_text(encoding='utf-8'))
                experiment_documents = json.loads((agents / 'knowledge_documents.json').read_text(encoding='utf-8'))
                self.documents = load_conversation_documents(experiment_documents,
                    self.root/'knowledge/diabetes_chat_documents.json')
                extended = load_extended_documents(self.root/'knowledge/diabetes_extended.json')
                extended += load_extended_documents(self.root/'knowledge/diabetes_expansion.json')
                self.documents.extend(extended)
                if len({d['doc_id'] for d in self.documents})!=len(self.documents):
                    raise ValueError('Duplicate knowledge document ID')
                self.examples = json.loads((agents / 'examples.json').read_text(encoding='utf-8'))
                model = core.Ch6MLP()
                model.load_state_dict(torch.load(model_root / 'diabetes/pima_mlp_state.pt', map_location='cpu', weights_only=True))
                model.eval()
                torch.set_num_threads(1)
                self.predictor = core.Ch6PredictionAgent(model,
                    joblib.load(model_root / 'diabetes/pima_preprocessor.joblib'), self.metadata['threshold'])
                index = joblib.load(agents / 'knowledge_index.joblib')
                knowledge = object.__new__(core.Ch6KnowledgeAgent)
                knowledge.documents = experiment_documents
                knowledge.by_id = {d['doc_id']: d for d in experiment_documents}
                for name in ['vectorizer', 'matrix', 'lsa', 'dense_matrix', 'thresholds']:
                    setattr(knowledge, name, index[name])
                knowledge.graph = nx.node_link_graph(json.loads((agents / 'knowledge_graph.json').read_text(encoding='utf-8')))
                knowledge.facts = [(d['subject'], d['relation'], d['object'], d['evidence_id'])
                    for _, _, d in knowledge.graph.edges(data=True) if 'subject' in d]
                self.knowledge = knowledge
                self.dialogue = DiabetesDialogue(knowledge,self.documents,extended)
                self.safety = core.Ch6SafetyAgent(self.documents)
                self.q_table = np.load(agents / 'q_table.npy', allow_pickle=False)
                if self.q_table.shape != (32, 5) or not np.isfinite(self.q_table).all():
                    raise ValueError('Invalid Q-table')
                self.q_table.setflags(write=False)
                self.core = core
                self.manifest = manifest
                self._loaded = True
            except ModelUnavailableError:
                raise
            except ImportError as exc:
                raise ModelUnavailableError('Trợ lý chưa đủ thư viện để hoạt động. Cài requirements.txt trong môi trường Python 3.11 trở lên.') from exc
            except Exception as exc:
                LOGGER.exception('Could not load Chapter 6 artifacts')
                raise ModelUnavailableError('Chưa nạp được dữ liệu của trợ lý. Chạy scripts/export_chapter6_project.py rồi khởi động lại.') from exc

    def health(self):
        self.ensure_loaded()
        return dict(status='ready', service='diabetes-multi-agent', model_version=self.manifest['model_version'],
            prediction=True, knowledge=True, q_learning=True, documents=len(self.documents),
            knowledge_graph=self.dialogue.statistics(),
            knowledge_engine='TF-IDF / LSA + local graph + Vietnamese topic expansion', response_mode='source-backed extractive',
            storage='SQLite', q_seed=self.manifest['q_seed'])

    def configuration(self):
        self.ensure_loaded()
        return dict(fields=[dict(key=k, label=label, display_unit=display_unit, unit=unit, step=step)
                    for k, label, display_unit, unit, step in FEATURE_FIELDS],
            examples=[{key:value for key,value in e.items() if key!='expected_prediction'} for e in self.examples],
            model_version=self.manifest['model_version'], threshold=self.metadata['threshold'],
            suggested_queries=['A1C cho biết điều gì trong kế hoạch chăm sóc?',
                'Xét nghiệm nào theo dõi chức năng thận?', 'Làm sao lập kế hoạch bữa ăn khi có tiểu đường?',
                'Hoạt động thể chất có vai trò gì?'])

    def validate(self, profile, query='', mode='predict_explain', units=None):
        self.ensure_loaded()
        return self.safety.preflight(profile, query, mode=='predict_explain', units)

    def predict(self, profile, units=None):
        self.ensure_loaded()
        decision = self.validate(profile, units=units)
        if decision['status'] != 'ALLOW':
            return dict(safety=decision, prediction=None)
        started = time.perf_counter()
        prediction = self.predictor.predict(profile)
        self.safety.validate_results(prediction, [], [], True)
        return dict(safety=decision, prediction=prediction, latency_ms=(time.perf_counter()-started)*1000)

    def search(self, query, k=3, method='Hybrid'):
        self.ensure_loaded()
        decision = self.validate({}, query, 'knowledge')
        if decision['status'] != 'ALLOW':
            return dict(safety=decision, evidence=[], blocks=[], graph=[])
        started = time.perf_counter()
        understanding = self.dialogue.understand(query)
        evidence = self.dialogue.search(query,k=k,method=method,understanding=understanding)
        blocks = self.knowledge.answer(evidence)
        final = self.safety.validate_results(None, evidence, blocks, False)
        return dict(safety=final, evidence=evidence, blocks=blocks, graph=self.graph_facts(evidence),understanding=understanding,
                    latency_ms=(time.perf_counter()-started)*1000)

    def graph_facts(self, evidence):
        ids = {h['doc_id'] for h in evidence}
        return [dict(source=s, relation=r, target=o, evidence_id=e) for s,r,o,e in self.dialogue.facts if e in ids]

    @staticmethod
    def public_task(task, include_inputs=True):
        result = {key:copy.deepcopy(value) for key,value in task.items() if key not in ['profile','units','_prediction_dialogue']}
        if include_inputs:
            result['inputs'] = dict(profile=copy.deepcopy(task['profile']), units=copy.deepcopy(task['units']))
        return result

    def task_status(self, task_id, owner_id):
        return self.public_task(self.store.get(task_id, owner_id))

    def history(self, owner_id, limit=20):
        return [{key:t.get(key) for key in ['task_id','query','mode','policy','status','outcome',
                'created_at','updated_at','latency_ms','tool_calls','turns']}
                for t in self.store.history(owner_id, limit)]

    def conversation(self, owner_id, conversation_id):
        tasks=self.store.conversation(owner_id,conversation_id)
        if not tasks:
            raise KeyError('Conversation not found')
        return [self.public_task(task,include_inputs=False) for task in tasks]

    def chat(self, owner_id, message, conversation_id=None):
        """Choose the chat route on the server; the browser submits only a message."""
        self.ensure_loaded()
        with self._lock:
            previous=[]
            if conversation_id:
                previous=self.store.conversation(owner_id,conversation_id)
                if not previous:
                    raise KeyError('Conversation not found')
                if len(previous)>=60:
                    raise TaskConflictError('Cuộc trò chuyện đã đủ 60 tin nhắn. Hãy mở cuộc trò chuyện mới.')
            else:
                conversation_id=uuid.uuid4().hex
            tick=time.perf_counter()
            completed=prediction_followup(message,previous)
            if completed is not None:
                plan=dict(route='prediction_result',topics=['prediction'],uses_context=True,
                    prediction_required=False,tools=[],
                    steps=['Tìm kết quả đã chạy trong cuộc trò chuyện','Kiểm tra yêu cầu','Giải thích nhóm dự đoán'],
                    reason='Giải thích kết quả đã có; không thu thập lại chỉ số và không gọi lại mô hình.')
                return self.execute(owner_id,dict(query=message,mode='knowledge',policy='rule',
                    conversation_id=conversation_id,conversation_turn=len(previous)+1,plan=plan,
                    prediction_reference=completed['task_id'],
                    conversation_reply=prediction_reply(completed['prediction'],
                        completed['_prediction_dialogue'].get('demo',False),followup=True)))
            request=prediction_request(message,previous,self.examples)
            if request is not None:
                plan=dict(route='prediction',topics=['prediction'],uses_context=bool(previous and
                    previous[-1].get('_prediction_dialogue',{}).get('active')),
                    prediction_required=True,tools=['prediction','knowledge_search','knowledge_graph'] if request['ready'] else [],
                    steps=['Nhận diện yêu cầu dự đoán','Thu thập chỉ số trong hội thoại','Kiểm tra dữ liệu và phạm vi',
                        'Gọi mô hình khi đủ dữ liệu','Giải thích điểm và tra cứu xét nghiệm'],
                    reason=('Đã đủ chỉ số và xác nhận phạm vi; gọi mô hình dự đoán rồi tra cứu thông tin xét nghiệm.'
                        if request['ready'] else 'Kiểm tra hồ sơ trước khi gọi mô hình; chưa chạy khi thiếu dữ liệu hoặc ngoài phạm vi.'))
                return self.execute(owner_id,dict(query=message,
                    mode='predict_explain' if request['ready'] else 'knowledge',policy='rule',
                    profile=request['state']['profile'] if request['ready'] else {},
                    units=request['state']['units'] if request['ready'] else {},
                    conversation_id=conversation_id,conversation_turn=len(previous)+1,plan=plan,
                    retrieval_query='Xét nghiệm chẩn đoán tiểu đường',
                    prediction_request=request,prediction_parse_ms=(time.perf_counter()-tick)*1000,
                    conversation_reply=request['reply']))
            normalized=normalize_question(message)
            intent=self.dialogue.understand(message)
            retrieval_query=message
            uses_context=False
            if not intent['topics'] and normalized not in ['xin chao','chao','hello','hi','cam on','thank you']:
                # Use context only for explicit follow-up phrasing. Independent
                # unrelated questions must retain the no-evidence outcome.
                followup=normalized.startswith(('con ','vay ','the ','nhung loai','loai nao','noi ro','ke them'))
                if followup:
                    last=next((t for t in reversed(previous) if t.get('understanding',{}).get('topics')),None)
                    if last:
                        retrieval_query=last.get('retrieval_query',last['query'])+'\n'+message
                        intent=self.dialogue.understand(retrieval_query)
                        uses_context=True
            greeting=normalized in ['xin chao','chao','hello','hi','cam on','thank you']
            plan=dict(route='conversation' if greeting else 'knowledge',
                topics=intent['topics'],uses_context=uses_context,
                tools=[] if greeting else ['knowledge_search','knowledge_graph'],
                prediction_required=False,
                steps=(['Tiếp nhận tin nhắn','Kiểm tra phạm vi','Trả lời giao tiếp'] if greeting else
                    ['Tiếp nhận và hiểu câu hỏi','Chọn tài liệu theo chủ đề',
                     'Truy xuất tài liệu và quan hệ tri thức','Kiểm chứng nguồn','Tổng hợp câu trả lời']),
                reason=('Tin nhắn giao tiếp, không cần gọi mô hình hoặc truy xuất tài liệu.' if greeting else
                    'Câu hỏi cần thông tin có nguồn; chọn truy xuất tri thức. Mô hình dự đoán không cần cho yêu cầu này.'))
            reply=None
            if greeting:
                reply=('Rất vui được hỗ trợ bạn. Bạn muốn tìm hiểu thêm về vấn đề nào liên quan đến tiểu đường?'
                       if normalized in ['cam on','thank you'] else
                       'Chào bạn! Tôi có thể hỗ trợ tìm hiểu về tiểu đường, dinh dưỡng, vận động và các xét nghiệm. Bạn muốn hỏi điều gì?')
            result = self.execute(owner_id,dict(query=message,mode='knowledge',policy='rule',
                conversation_id=conversation_id,conversation_turn=len(previous)+1,
                retrieval_query=retrieval_query,plan=plan,conversation_reply=reply))
        # Network synthesis must not hold the global model/workflow lock.
        if result['outcome']=='ANSWERED' and result['evidence']:
            composed = self.synthesis.compose(retrieval_query,result['evidence'])
            if composed:
                task = self.store.get(result['task_id'],owner_id)
                revision = task['revision']
                duration = composed.get('duration_ms',0)
                task['trace'].append(dict(session_id=owner_id,task_id=task['task_id'],sender='Knowledge',
                    receiver='Coordinator',action='COMPOSE_ASSISTED_RESPONSE',payload={},
                    status='COMPLETED' if composed['status']=='completed' else 'FALLBACK',
                    evidence_ids=[h['doc_id'] for h in task['evidence']],safety_status=task['safety_status'],
                    timestamp=utc_now(),duration_ms=duration,turn=task['turns']))
                if composed['status']=='completed':
                    task['answer_blocks'] = composed['blocks']
                task['latency_ms'] += duration
                task['total_latency_ms'] += duration
                if duration:
                    task['tool_calls'] += 1
                self.store.save(task,owner_id,revision)
                result = self.public_task(task)
        return result

    def execute(self, owner_id, payload):
        self.ensure_loaded()
        with self._lock:
            revision = None
            if payload.get('task_id'):
                task = self.store.get(payload['task_id'], owner_id)
                revision = task['revision']
                if task['outcome'] not in ['REQUEST_INFO','NO_EVIDENCE']:
                    raise TaskConflictError('Yêu cầu này đã kết thúc. Hãy tạo yêu cầu mới.')
                if task['turns'] >= 8:
                    raise TaskConflictError('Đã đạt giới hạn bổ sung thông tin. Hãy tạo yêu cầu mới.')
                for key in ['mode','policy']:
                    if key in payload and payload[key] != task[key]:
                        raise TaskConflictError('Chế độ đã thay đổi. Hãy tạo yêu cầu mới.')
                if 'profile' in payload:
                    task['profile'].update(payload['profile'])
                    task['prediction'] = None
                task['units'].update(payload.get('units', {}))
                if 'query' in payload and payload['query'] != task['query']:
                    task['query'] = payload['query']
                    task['evidence'], task['blocks'] = [], []
            else:
                task = dict(task_id=uuid.uuid4().hex, query=payload['query'],
                    profile=copy.deepcopy(payload.get('profile', {})), units=copy.deepcopy(payload.get('units', {})),
                    mode=payload.get('mode','predict_explain'), policy=payload.get('policy','rule'),
                    status='PENDING', outcome=None, safety_status='UNKNOWN', reasons=[],
                    prediction=None, evidence=[], blocks=[], graph=[], trace=[], tool_calls=0,
                    turns=0, total_latency_ms=0.0)
                if payload.get('conversation_id'):
                    task.update(conversation_id=payload['conversation_id'],
                        conversation_turn=payload['conversation_turn'],
                        retrieval_query=payload.get('retrieval_query',payload['query']),
                        plan=copy.deepcopy(payload['plan']))
                    if payload.get('prediction_request'):
                        task['_prediction_dialogue']=copy.deepcopy(payload['prediction_request']['state'])
            task['turns'] += 1
            task['status'] = 'RUNNING'
            task['prediction'] = None if task['mode']=='knowledge' else task['prediction']
            task['blocks'] = []
            started = time.perf_counter()
            calls, steps = 0, 0

            def event(sender, action, duration_ms, status='COMPLETED', details=None):
                task['trace'].append(dict(session_id=owner_id, task_id=task['task_id'],
                    sender=sender, receiver='Coordinator', action=action, payload=details or {},
                    status=status, evidence_ids=[h['doc_id'] for h in task['evidence']],
                    safety_status=task['safety_status'], timestamp=utc_now(),
                    duration_ms=duration_ms, turn=task['turns']))

            def run(sender, action, function):
                tick = time.perf_counter()
                try:
                    value = function()
                except Exception as exc:
                    event(sender, action, (time.perf_counter()-tick)*1000, 'FAILED',
                          dict(error_type=type(exc).__name__))
                    raise
                event(sender, action, (time.perf_counter()-tick)*1000)
                return value

            def budget():
                if time.perf_counter()-started > 5:
                    raise TimeoutError('Workflow deadline reached')
                if calls >= 6:
                    raise RuntimeError('Tool call budget reached')

            needs_prediction = task['mode']=='predict_explain'
            try:
                if task.get('plan'):
                    event('Coordinator','PLAN_WORKFLOW',0,details=dict(
                        route=task['plan']['route'],tools=task['plan']['tools'],
                        uses_context=task['plan']['uses_context']))
                if payload.get('prediction_request'):
                    request=payload['prediction_request']
                    event('Coordinator','COLLECT_PREDICTION_INPUTS',payload['prediction_parse_ms'],details=dict(
                        received_fields=list(request['state']['profile']),missing=request['missing'],
                        issues=request['issues'],ready=request['ready'],demo=request['state']['demo']))
                decision = run('Safety','VALIDATE_INPUT',lambda:self.safety.preflight(
                    task['profile'],task['query'],needs_prediction,task['units']))
                task['safety_status'],task['reasons'] = decision['status'],decision['reasons']
                event('Safety','INPUT_DECISION',0,details={'decision':decision['status']})
                if decision['status'] != 'ALLOW':
                    task['prediction'],task['evidence'],task['graph'] = None,[],[]
                    task['status'],task['outcome'] = 'REQUIRES_REVIEW',decision['status']
                elif payload.get('conversation_reply'):
                    outcome=payload.get('prediction_request',{}).get('outcome','ANSWERED')
                    task.update(status='AWAITING_INPUT' if outcome=='REQUEST_INFO' else 'COMPLETED',
                                outcome=outcome,reply=payload['conversation_reply'],reasons=[],
                                safety_status='REQUEST_INFO' if outcome!='ANSWERED' else 'ALLOW')
                    if payload.get('prediction_reference'):
                        task['prediction_reference']=payload['prediction_reference']
                        event('Coordinator','EXPLAIN_PREDICTION_RESULT',0,details=dict(
                            source_task_id=payload['prediction_reference']))
                    event('Coordinator','RESPOND_CONVERSATION',0)
                else:
                    while True:
                        if steps >= 10 or time.perf_counter()-started > 5:
                            raise RuntimeError('Workflow budget reached')
                        steps += 1
                        p = (0 if task['prediction'] is None else
                             1 + int(task['prediction']['score'] >= 1/3) + int(task['prediction']['score'] >= 2/3))
                        state = (1,p,int(bool(task['evidence'])),0)
                        if not needs_prediction:
                            action = self.core.CH6_RETRIEVE if not task['evidence'] else self.core.CH6_RESPOND
                        elif task['policy']=='q_learning':
                            action = self.core.ch6_q_policy(self.q_table,state)
                        else:
                            action = self.core.ch6_rule_policy(state)
                        if needs_prediction and action not in self.core.ch6_valid_actions(state):
                            raise RuntimeError('Invalid proposed action')
                        event('Coordinator','SELECT_ACTION',0,details=dict(action=self.core.CH6_ACTIONS[action]))
                        if action == self.core.CH6_PREDICT:
                            budget();calls += 1
                            prediction = run('Prediction','RUN_PREDICTION',lambda:self.predictor.predict(task['profile']))
                            run('Safety','VALIDATE_PREDICTION',lambda:self.safety.validate_results(prediction,[],[],True))
                            task['prediction'] = prediction
                        elif action == self.core.CH6_RETRIEVE:
                            understanding = run('Knowledge','UNDERSTAND_QUERY',
                                                lambda:self.dialogue.understand(task.get('retrieval_query',task['query'])))
                            task['understanding'] = understanding
                            event('Knowledge','QUERY_TOPICS',0,details={'topics':understanding['topics']})
                            for attempt in range(2):
                                budget();calls += 1
                                try:
                                    hits = run('Knowledge','RETRIEVE_KNOWLEDGE',lambda:self.dialogue.search(
                                        task.get('retrieval_query',task['query']),understanding=understanding))
                                    run('Safety','VALIDATE_EVIDENCE',lambda:self.safety.validate_results(None,hits,[],False))
                                    task['evidence'] = hits
                                    if hits:
                                        task['graph']=run('Knowledge','LOOKUP_GRAPH',lambda:self.graph_facts(hits))
                                    break
                                except TimeoutError:
                                    if attempt==1: raise
                            if not task['evidence']:
                                task.update(status='REQUIRES_REVIEW',outcome='NO_EVIDENCE',safety_status='REQUEST_INFO',
                                    reasons=['Chưa tìm thấy bằng chứng phù hợp. Hãy đặt câu hỏi cụ thể hơn về tiểu đường.'])
                                break
                        elif action == self.core.CH6_RESPOND:
                            blocks = run('Knowledge','COMPOSE_EXTRACTIVE_RESPONSE',lambda:self.knowledge.answer(task['evidence']))
                            final = run('Safety','VALIDATE_RESPONSE',lambda:self.safety.validate_results(
                                task['prediction'],task['evidence'],blocks,needs_prediction))
                            if final['status'] != 'ALLOW': raise ValueError('Response validation failed')
                            task.update(status='COMPLETED',outcome='ANSWERED',safety_status='ALLOW',reasons=[],blocks=blocks)
                            event('Safety','RESPONSE_DECISION',0,details={'decision':'ALLOW'})
                            break
                        else:
                            raise RuntimeError('Unexpected workflow action')
            except Exception:
                LOGGER.exception('Chapter 6 workflow failed: task=%s',task['task_id'])
                task.update(status='FAILED',outcome='TOOL_OR_BUDGET_ERROR',safety_status='ESCALATE',
                    blocks=[],reasons=['Không hoàn thành được yêu cầu do lỗi công cụ hoặc giới hạn xử lý. Hãy thử lại bằng yêu cầu mới.'])
            task['latency_ms'] = (time.perf_counter()-started)*1000
            if payload.get('prediction_request'):
                if task['prediction'] is not None and task['outcome']=='ANSWERED':
                    task['reply']=prediction_reply(task['prediction'],task['_prediction_dialogue']['demo'])
                    task['_prediction_dialogue']['active']=False
                elif task['outcome']=='ESCALATE':
                    task['_prediction_dialogue']['active']=False
            task['total_latency_ms'] += task['latency_ms']
            task['tool_calls'] += calls
            task['steps'] = steps
            task['graph'] = self.graph_facts(task['evidence'])
            # Malformed numerical input is reported to the owner but never stored as NaN/Infinity.
            for key,value in task['profile'].items():
                if isinstance(value,float) and not math.isfinite(value): task['profile'][key] = None
            self.store.save(task,owner_id,revision)
            return self.public_task(task)
