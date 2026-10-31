"""Chapter 6 page and versioned APIs; browser sessions own their task history."""
import hmac
import re
import secrets
import threading

from flask import Blueprint, current_app, jsonify, render_template, request, session
from werkzeug.exceptions import BadRequest, Forbidden, HTTPException, RequestEntityTooLarge, UnsupportedMediaType

from mvc.models.agents_model import AgentsModel, FEATURE_FIELDS
from mvc.models.model_errors import ModelUnavailableError, TaskConflictError

agents_bp = Blueprint('agents', __name__)
_service_lock = threading.Lock()


def get_agents_model():
    with _service_lock:
        if 'chapter6_agents' not in current_app.extensions:
            current_app.extensions['chapter6_agents'] = AgentsModel(
                current_app.config.get('AGENTS_ROOT', current_app.root_path),
                current_app.config['AGENTS_DATABASE'],
                external_enabled=False if current_app.testing else current_app.config.get('ASSISTANT_EXTERNAL_ENABLED'))
    return current_app.extensions['chapter6_agents']


def prepare_session():
    session.setdefault('agents_owner', secrets.token_hex(24))
    session.setdefault('agents_csrf', secrets.token_hex(32))
    return session['agents_owner']


@agents_bp.before_request
def protect_request():
    if request.content_length is not None and request.content_length > 32768:
        raise RequestEntityTooLarge('Nội dung yêu cầu vượt quá 32 KB.')
    if request.method in ['POST','PUT','PATCH','DELETE']:
        expected = session.get('agents_csrf')
        supplied = request.headers.get('X-CSRF-Token', '')
        if not expected or not session.get('agents_owner') or not hmac.compare_digest(expected.encode(), supplied.encode()):
            raise Forbidden('Phiên không hợp lệ. Tải lại trang để tiếp tục.')


@agents_bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def payload(allowed):
    if not request.is_json:
        raise UnsupportedMediaType('API yêu cầu Content-Type: application/json.')
    value = request.get_json()
    if not isinstance(value, dict):
        raise BadRequest('Nội dung JSON phải là một đối tượng.')
    if set(value) - set(allowed):
        raise BadRequest('Có trường dữ liệu không được hỗ trợ.')
    return value


def validate_input(value, require_query=False):
    if 'query' in value:
        if not isinstance(value['query'], str) or not value['query'].strip() or len(value['query']) > 2000:
            raise BadRequest('Câu hỏi cần từ 1 đến 2.000 ký tự.')
        value['query'] = value['query'].strip()
    elif require_query:
        raise BadRequest('Vui lòng nhập câu hỏi.')
    feature_keys = {field[0] for field in FEATURE_FIELDS}
    for field in ['profile','units']:
        if field in value:
            if not isinstance(value[field],dict) or set(value[field])-feature_keys:
                raise BadRequest('Hồ sơ hoặc đơn vị có trường không hợp lệ.')
            for v in value[field].values():
                if not isinstance(v,(str,int,float,bool,type(None))) or (isinstance(v,str) and len(v)>64):
                    raise BadRequest('Mỗi chỉ số phải là một giá trị đơn.')
                if isinstance(v,int) and abs(v)>10**12:
                    raise BadRequest('Chỉ số vượt phạm vi dữ liệu được hỗ trợ.')
            if field=='units' and any(not isinstance(v,str) for v in value[field].values()):
                raise BadRequest('Đơn vị phải là chuỗi ký tự.')
    if 'mode' in value and value['mode'] not in ['predict_explain','knowledge']:
        raise BadRequest('Chế độ không hợp lệ.')
    if 'policy' in value and value['policy'] not in ['rule','q_learning']:
        raise BadRequest('Chính sách không hợp lệ.')
    if 'task_id' in value and (not isinstance(value['task_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',value['task_id'])):
        raise BadRequest('Mã yêu cầu không hợp lệ.')
    return value


@agents_bp.route('/agents')
def index():
    prepare_session()
    return render_template('agents.html', active_tab='agents', csrf_token=session['agents_csrf'],
        fields=[dict(key=k,label=label,display_unit=display_unit,unit=unit,step=step)
                for k,label,display_unit,unit,step in FEATURE_FIELDS])


@agents_bp.get('/api/v1/agents/session')
def session_configuration():
    prepare_session()
    return jsonify(success=True, csrf_token=session['agents_csrf'], config=get_agents_model().configuration())


@agents_bp.get('/api/v1/health')
def health():
    return jsonify(success=True, **get_agents_model().health())


@agents_bp.post('/api/v1/assistant/chat')
def assistant_chat():
    value=payload(['message','conversation_id'])
    message=value.get('message')
    if not isinstance(message,str) or not message.strip() or len(message)>2000:
        raise BadRequest('Tin nhắn cần từ 1 đến 2.000 ký tự.')
    conversation_id=value.get('conversation_id')
    if conversation_id is not None and (not isinstance(conversation_id,str) or not re.fullmatch(r'[a-f0-9]{32}',conversation_id)):
        raise BadRequest('Mã cuộc trò chuyện không hợp lệ.')
    task=get_agents_model().chat(session['agents_owner'],message.strip(),conversation_id)
    return jsonify(success=True,task=task,conversation_id=task['conversation_id'])


@agents_bp.get('/api/v1/assistant/conversations')
def assistant_conversations():
    if not session.get('agents_owner'):
        return jsonify(success=True,conversations=[])
    return jsonify(success=True,conversations=get_agents_model().store.conversations(session['agents_owner']))


@agents_bp.get('/api/v1/assistant/conversations/<conversation_id>')
def assistant_conversation(conversation_id):
    if not session.get('agents_owner'):
        return jsonify(success=False,error='Không tìm thấy cuộc trò chuyện.'),404
    return jsonify(success=True,tasks=get_agents_model().conversation(session['agents_owner'],conversation_id))


@agents_bp.delete('/api/v1/assistant/conversations')
def clear_assistant_conversations():
    return jsonify(success=True,deleted=get_agents_model().store.clear_conversations(session['agents_owner']))


@agents_bp.post('/api/v1/agents/execute')
def execute():
    value = payload(['query','profile','units','mode','policy','task_id'])
    validate_input(value, require_query=not bool(value.get('task_id')))
    task = get_agents_model().execute(session['agents_owner'],value)
    return jsonify(success=True, task=task)


@agents_bp.get('/api/v1/agents/status/<task_id>')
def status(task_id):
    if not session.get('agents_owner'):
        return jsonify(success=False,error='Không tìm thấy yêu cầu.'),404
    return jsonify(success=True,task=get_agents_model().task_status(task_id,session['agents_owner']))


@agents_bp.post('/api/v1/agents/compare')
def compare_policies():
    value = validate_input(payload(['query','profile','units']),require_query=True)
    model = get_agents_model()
    tasks = [model.execute(session['agents_owner'],{**value,'mode':'predict_explain','policy':policy})
             for policy in ['rule','q_learning']]
    return jsonify(success=True,tasks=tasks)


@agents_bp.get('/api/v1/agents/history')
def history():
    if not session.get('agents_owner'):
        return jsonify(success=True,tasks=[])
    raw_limit = request.args.get('limit','20')
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise BadRequest('Giới hạn lịch sử không hợp lệ.') from exc
    if not 1<=limit<=50:
        raise BadRequest('Giới hạn lịch sử cần từ 1 đến 50.')
    return jsonify(success=True,tasks=get_agents_model().history(session['agents_owner'],limit))


@agents_bp.delete('/api/v1/agents/history')
def clear_history():
    deleted = get_agents_model().store.clear(session['agents_owner'])
    return jsonify(success=True,deleted=deleted)


@agents_bp.post('/api/v1/predict')
def predict():
    value = validate_input(payload(['profile','units']))
    return jsonify(success=True,**get_agents_model().predict(value.get('profile',{}),value.get('units')))


@agents_bp.post('/api/v1/knowledge/search')
def search():
    value = validate_input(payload(['query','top_k','method']),require_query=True)
    k = value.get('top_k',3)
    if type(k) is not int or not 1<=k<=10:
        raise BadRequest('top_k cần là số nguyên từ 1 đến 10.')
    method = value.get('method','Hybrid')
    if method not in ['TF-IDF','LSA','Hybrid']:
        raise BadRequest('Phương pháp truy xuất không hợp lệ.')
    return jsonify(success=True,**get_agents_model().search(value['query'],k,method))


@agents_bp.post('/api/v1/safety/validate')
def validate_safety():
    value = validate_input(payload(['profile','query','mode','units']))
    return jsonify(success=True,safety=get_agents_model().validate(value.get('profile',{}),
        value.get('query',''),value.get('mode','predict_explain'),value.get('units')))


@agents_bp.errorhandler(HTTPException)
def http_error(error):
    return jsonify(success=False,error=error.description),error.code


@agents_bp.errorhandler(ModelUnavailableError)
def unavailable(error):
    return jsonify(success=False,status='unavailable',error=str(error)),503


@agents_bp.errorhandler(TaskConflictError)
def conflict(error):
    return jsonify(success=False,error=str(error)),409


@agents_bp.errorhandler(KeyError)
def missing_task(error):
    return jsonify(success=False,error='Không tìm thấy yêu cầu trong phiên hiện tại.'),404


@agents_bp.errorhandler(Exception)
def unexpected_error(error):
    current_app.logger.exception('Unexpected Chapter 6 API error')
    return jsonify(success=False,error='Không xử lý được yêu cầu. Vui lòng thử lại.'),500
