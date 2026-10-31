"""Local-only browser check through Chrome DevTools; no external accounts."""
import base64
import json
import subprocess
import sys
import time
import uuid
import socket
from pathlib import Path

import requests
import websocket

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/project'
OUT.mkdir(parents=True,exist_ok=True)
PROFILE = ROOT / '.ipynb_checkpoints' / ('chrome-agents-'+uuid.uuid4().hex)
CHROME = next((p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
    Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')]
    if p.exists()),None)
HTTP = requests.Session()
HTTP.trust_env = False
CHECKS, EXCEPTIONS = [], []


class Browser:
    def __init__(self,url):
        self.socket = websocket.create_connection(url,suppress_origin=True,timeout=20)
        self.counter = 0

    def call(self,method,params=None):
        self.counter += 1
        mid = self.counter
        self.socket.send(json.dumps(dict(id=mid,method=method,params=params or {})))
        while True:
            message = json.loads(self.socket.recv())
            if message.get('method')=='Runtime.exceptionThrown':
                EXCEPTIONS.append(message['params']['exceptionDetails'])
            if message.get('id')==mid:
                if 'error' in message: raise RuntimeError(message['error'])
                return message.get('result',{})

    def js(self,expression):
        result = self.call('Runtime.evaluate',dict(expression=expression,awaitPromise=True,returnByValue=True))
        if 'exceptionDetails' in result:
            raise RuntimeError(result['exceptionDetails'])
        return result.get('result',{}).get('value')

    def wait(self,expression,seconds=25):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            if self.js(expression): return
            time.sleep(.15)
        raise RuntimeError('DOM condition not reached: '+expression)

    def screenshot(self,name):
        layout = self.call('Page.getLayoutMetrics')['cssContentSize']
        self.call('Emulation.setPageScaleFactor',{'pageScaleFactor':1})
        data = self.call('Page.captureScreenshot',dict(format='png',captureBeyondViewport=True,
            clip=dict(x=0,y=0,width=layout['width'],height=layout['height'],scale=1)))
        (OUT/name).write_bytes(base64.b64decode(data['data']))


def check(name,condition):
    if not condition: raise AssertionError(name)
    CHECKS.append(name)
    print('PASS',name,flush=True)


def main():
    if CHROME is None:
        raise RuntimeError('Browser check requires Chrome or Edge on Windows.')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0))
        debug_port=listener.getsockname()[1]
    process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run',
        '--no-default-browser-check','--remote-debugging-port='+str(debug_port),'--window-size=1440,1100',
        '--user-data-dir='+str(PROFILE),'http://127.0.0.1:5000/agents'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    browser=None
    try:
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                tabs=HTTP.get('http://127.0.0.1:'+str(debug_port)+'/json/list',timeout=1).json()
                tab=next(t for t in tabs if t.get('type')=='page')
                break
            except (requests.RequestException,StopIteration):time.sleep(.2)
        else:raise RuntimeError('Chrome did not start')
        browser=Browser(tab['webSocketDebuggerUrl'])
        browser.call('Runtime.enable');browser.call('Page.enable')
        browser.wait("document.getElementById('sendMessage') && !document.getElementById('sendMessage').disabled")
        check('chat_only_no_numeric_form_or_mode_selector',browser.js("!document.querySelector('#agentsApp input[type=number]') && !document.getElementById('agentPolicy') && !document.querySelector('[data-mode]')"))
        check('desktop_chat_left_orchestration_right',browser.js("document.querySelector('.chat-panel').getBoundingClientRect().right < document.querySelector('.orchestration-panel').getBoundingClientRect().left"))
        before_width=browser.js("document.getElementById('chatPanel').getBoundingClientRect().width")
        split=browser.js("(()=>{const r=document.getElementById('paneResize').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+90}})()")
        browser.call('Input.dispatchMouseEvent',dict(type='mouseMoved',x=split['x'],y=split['y']))
        browser.call('Input.dispatchMouseEvent',dict(type='mousePressed',x=split['x'],y=split['y'],button='left',buttons=1,clickCount=1))
        browser.call('Input.dispatchMouseEvent',dict(type='mouseMoved',x=split['x']-110,y=split['y'],button='left',buttons=1))
        browser.call('Input.dispatchMouseEvent',dict(type='mouseReleased',x=split['x']-110,y=split['y'],button='left',buttons=0,clickCount=1))
        check('splitter_drag_changes_both_panes',browser.js("document.getElementById('chatPanel').getBoundingClientRect().width")<before_width-60)
        browser.js("document.getElementById('paneResize').focus()")
        browser.call('Input.dispatchKeyEvent',dict(type='keyDown',key='End',code='End',windowsVirtualKeyCode=35))
        browser.call('Input.dispatchKeyEvent',dict(type='keyUp',key='End',code='End',windowsVirtualKeyCode=35))
        check('splitter_keyboard_accessible_and_clamped',browser.js("document.getElementById('paneResize').getAttribute('aria-valuenow')==='70' && Number(localStorage.getItem('diabetes-chat-share'))===70"))
        browser.call('Page.reload')
        browser.wait("document.getElementById('sendMessage') && !document.getElementById('sendMessage').disabled")
        check('splitter_ratio_restores_after_reload',browser.js("document.getElementById('paneResize').getAttribute('aria-valuenow')==='70'"))
        browser.js("document.getElementById('paneResize').dispatchEvent(new MouseEvent('dblclick',{bubbles:true}))")
        check('shared_blue_white_palette',browser.js("getComputedStyle(document.getElementById('sendMessage')).backgroundColor==='rgb(37, 99, 235)' && getComputedStyle(document.querySelector('.assistant-card')).backgroundColor==='rgb(255, 255, 255)'"))
        check('branding_has_no_academic_labels',browser.js("document.title.includes('Trợ lý tiểu đường') && !/đa tác tử|chương\\s*0?6|phân tích chỉ số/i.test(document.body.innerText+' '+document.title)"))
        check('desktop_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth+2"))
        def send_message(text,enter=False):
            count=browser.js("document.querySelectorAll('.assistant-message.assistant[data-task-id]').length")
            browser.js("document.getElementById('chatInput').value="+json.dumps(text)+";document.getElementById('chatInput').focus()")
            if enter:
                browser.call('Input.dispatchKeyEvent',dict(type='keyDown',key='Enter',code='Enter',windowsVirtualKeyCode=13))
                browser.call('Input.dispatchKeyEvent',dict(type='keyUp',key='Enter',code='Enter',windowsVirtualKeyCode=13))
            else:
                browser.js("document.getElementById('sendMessage').click()")
            browser.wait("document.querySelectorAll('.assistant-message.assistant[data-task-id]').length==="+str(count+1)+" && !document.getElementById('sendMessage').disabled")
        send_message('Xin chào')
        check('greeting_uses_no_retrieval_or_prediction',browser.js("!document.getElementById('flow-rag').classList.contains('is-active') && !document.getElementById('flow-model').classList.contains('is-active') && document.getElementById('callsMetric').textContent.includes('0')"))
        send_message('Tiểu đường ăn được gì',enter=True)
        check('diet_answer_and_real_source_in_chat',browser.js("document.querySelectorAll('.assistant-message[data-task-id]')[1].textContent.includes('Rau ít tinh bột') && document.querySelectorAll('.assistant-message[data-task-id]')[1].querySelector('a').href.includes('niddk.nih.gov')"))
        check('real_trace_selects_rag_and_graph_not_prediction',browser.js("document.getElementById('flow-rag').classList.contains('is-active') && document.getElementById('flow-graph').classList.contains('is-active') && !document.getElementById('flow-model').classList.contains('is-active') && document.getElementById('executionTrace').textContent.includes('Tra cứu quan hệ đồ thị')"))
        browser.screenshot('agents_desktop.png')
        browser.screenshot('diet_question_fixed.png')
        send_message('Còn những loại nào nữa?')
        check('followup_context_persists_in_same_chat',browser.js("!document.getElementById('contextBadge').hidden && document.querySelectorAll('.assistant-message.user').length===3 && document.querySelectorAll('.assistant-message[data-task-id]')[2].textContent.includes('Rau ít tinh bột')"))
        send_message('Hoạt động thể chất có vai trò gì?')
        check('agent_switches_topic_without_manual_mode',browser.js("document.getElementById('contextBadge').hidden && document.querySelectorAll('.assistant-message[data-task-id]')[3].textContent.includes('Hoạt động thể chất') && document.getElementById('executionTrace').textContent.includes('Vận động')"))
        send_message('Quỹ đạo sao Hỏa dài bao nhiêu')
        check('unrelated_question_does_not_reuse_medical_answer',browser.js("document.querySelectorAll('.assistant-message[data-task-id]')[4].textContent.includes('Chưa đủ bằng chứng') && !document.querySelectorAll('.assistant-message[data-task-id]')[4].querySelector('.message-citation')"))
        send_message('Liệu có bị tiểu đường')
        check('diagnosis_question_gets_test_information_without_form',browser.js("document.querySelectorAll('.assistant-message[data-task-id]')[5].textContent.includes('xét nghiệm máu') && !document.getElementById('flow-model').classList.contains('is-active')"))
        browser.js("document.querySelectorAll('.message-inspect')[1].click()")
        check('selecting_earlier_message_restores_its_trace',browser.js("document.getElementById('executionTrace').textContent.includes('Dinh dưỡng') && document.getElementById('contextBadge').hidden"))
        before=browser.js("document.querySelectorAll('.assistant-message.user').length")
        browser.call('Page.reload')
        browser.wait("document.getElementById('chatStatus')?.textContent==='Đã mở lại' && !document.getElementById('sendMessage').disabled")
        check('conversation_and_messages_restore_after_reload',browser.js("document.querySelectorAll('.assistant-message.user').length==="+str(before)+" && document.getElementById('conversationSelect').value!==''"))
        send_message('Tiểu đường uống rưởu được không?')
        check('alcohol_question_has_answer_and_clickable_source',browser.js("(()=>{const n=[...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1);return n.textContent.includes('hạ đường huyết') && n.querySelector('.message-citation').href.includes('medlineplus')})()"))
        send_message('Tiểu đường tuýp 2 là gì?')
        check('type2_question_gets_definition',browser.js("[...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('sử dụng insulin kém hiệu quả')"))
        send_message('tiểu đường uống nước cam được khônh')
        check('juice_question_gets_answer_despite_typo',browser.js("[...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('Nước cam')"))
        check('provider_settings_are_hidden_from_product',browser.js("!document.querySelector('#agentsApp input[type=password]') && !/GEMINI_API_KEY|ASSISTANT_GEMINI_MODEL/.test(document.documentElement.innerHTML)"))
        browser.js("(()=>{const n=document.getElementById('chatMessages');n.style.scrollBehavior='auto';n.scrollTop=n.scrollHeight;})()")
        browser.screenshot('agents_desktop.png')
        browser.call('Emulation.setDeviceMetricsOverride',dict(width=390,height=844,deviceScaleFactor=1,mobile=True))
        check('mobile_chat_first_and_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth+2 && document.querySelector('.chat-panel').getBoundingClientRect().top < document.querySelector('.orchestration-panel').getBoundingClientRect().top"))
        browser.js("document.getElementById('chatMessages').scrollTop=document.getElementById('chatMessages').scrollHeight")
        browser.screenshot('agents_mobile.png')
        browser.js("document.getElementById('newConversation').click()")
        send_message('Tôi muốn đánh giá nguy cơ tiểu đường bằng các chỉ số sức khỏe')
        check('prediction_intent_requests_missing_fields_without_call',browser.js("[...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('Cần bổ sung') && !document.getElementById('flow-model').classList.contains('is-active') && document.getElementById('callsMetric').textContent.includes('0')"))
        send_message('Tôi là nữ, 47 tuổi; BMI=35,5')
        check('prediction_partial_data_remains_in_conversation',browser.js("[...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('Tuổi=47') && !document.getElementById('flow-model').classList.contains('is-active')"))
        send_message('Số lần mang thai=10; Glucose=68 mg/dL sau 2 giờ OGTT; huyết áp tâm trương=106 mmHg; nếp gấp da=23 mm; insulin huyết thanh sau 2 giờ=49 µU/mL; DPF=0,285')
        check('complete_chat_inputs_call_prediction_and_show_actual_score',browser.js("document.getElementById('flow-model').classList.contains('is-active') && document.getElementById('edge-model').classList.contains('is-active') && [...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('Điểm mô hình: 0.1314')"))
        check('prediction_trace_shows_real_call_and_cited_explanation',browser.js("document.getElementById('executionTrace').textContent.includes('Gọi mô hình dự đoán') && [...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).querySelector('.message-citation')!==null"))
        browser.call('Page.reload')
        browser.wait("document.getElementById('chatStatus')?.textContent==='Đã mở lại' && !document.getElementById('sendMessage').disabled")
        check('prediction_result_and_flow_restore_after_reload',browser.js("document.getElementById('flow-model').classList.contains('is-active') && document.getElementById('chatMessages').textContent.includes('Điểm mô hình: 0.1314')"))
        browser.call('Emulation.setDeviceMetricsOverride',dict(width=1440,height=1100,deviceScaleFactor=1,mobile=False))
        browser.js("(()=>{const n=document.getElementById('chatMessages');n.style.scrollBehavior='auto';n.scrollTop=n.scrollHeight;})()")
        browser.screenshot('prediction_chat_desktop.png')
        browser.call('Emulation.setDeviceMetricsOverride',dict(width=390,height=844,deviceScaleFactor=1,mobile=True))
        browser.js("document.getElementById('chatMessages').scrollTop=document.getElementById('chatMessages').scrollHeight")
        browser.screenshot('prediction_chat_mobile.png')
        browser.js("document.getElementById('newConversation').click()")
        send_message('Chạy thử dự đoán bằng dữ liệu mẫu')
        check('explicit_demo_uses_model_and_identifies_sample',browser.js("document.getElementById('flow-model').classList.contains('is-active') && [...document.querySelectorAll('.assistant-message[data-task-id]')].at(-1).textContent.includes('dữ liệu mẫu nghiên cứu')"))
        browser.js("document.getElementById('newConversation').click()")
        check('new_conversation_resets_ui_without_deleting_history',browser.js("document.querySelectorAll('.assistant-message.user').length===0 && document.getElementById('conversationSelect').options.length>1"))
        send_message('<img src=x onerror=\"window.assistantInjected=true\">')
        check('message_text_does_not_execute_html',browser.js("!window.assistantInjected && !document.querySelector('#chatMessages img')"))
        browser.js("document.getElementById('clearHistory').click()")
        browser.wait("document.getElementById('conversationSelect').options.length===1 && !document.getElementById('sendMessage').disabled")
        check('clear_own_conversation_history',browser.js("document.querySelectorAll('.assistant-message.user').length===0"))
        check('no_browser_javascript_exceptions',not EXCEPTIONS)
        (OUT/'browser_checks.json').write_text(json.dumps(dict(checks=CHECKS,passed=len(CHECKS),exceptions=EXCEPTIONS),ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        if browser:browser.socket.close()
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill()


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
