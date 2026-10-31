/* Chat, adjustable panes and actual workflow records. */
(() => {
    'use strict';
    const root=document.getElementById('agentsApp');
    if(!root)return;
    const $=id=>document.getElementById(id);
    const workspace=$('assistantWorkspace'),splitter=$('paneResize');
    function setSplit(value,save=true){
        const ratio=Math.max(30,Math.min(70,Number(value)||55));
        workspace.style.setProperty('--chat-share',ratio+'fr');
        workspace.style.setProperty('--flow-share',(100-ratio)+'fr');
        splitter.setAttribute('aria-valuenow',String(Math.round(ratio)));
        if(save){try{localStorage.setItem('diabetes-chat-share',String(ratio));}catch{}}
    }
    try{setSplit(localStorage.getItem('diabetes-chat-share'),false);}catch{setSplit(55,false);}
    splitter.addEventListener('pointerdown',event=>{if(event.button!==0)return;splitter.setPointerCapture(event.pointerId);workspace.classList.add('is-resizing');event.preventDefault();});
    splitter.addEventListener('pointermove',event=>{if(!splitter.hasPointerCapture(event.pointerId))return;const box=workspace.getBoundingClientRect();setSplit((event.clientX-box.left)/box.width*100);});
    ['pointerup','pointercancel','lostpointercapture'].forEach(name=>splitter.addEventListener(name,()=>workspace.classList.remove('is-resizing')));
    splitter.addEventListener('keydown',event=>{let value=Number(splitter.getAttribute('aria-valuenow'));if(event.key==='ArrowLeft')value-=2;else if(event.key==='ArrowRight')value+=2;else if(event.key==='Home')value=30;else if(event.key==='End')value=70;else return;event.preventDefault();setSplit(value);});
    splitter.addEventListener('dblclick',()=>setSplit(55));
    let csrf=root.dataset.csrf,ready=false,busy=false,conversationId=null;
    const topics={nutrition:'Dinh dưỡng',activity:'Vận động',symptoms:'Triệu chứng',a1c:'Theo dõi A1C',tests:'Xét nghiệm',kidney:'Chức năng thận',prevention:'Phòng ngừa',hypoglycemia:'Hạ đường huyết',medicines:'Thông tin thuốc',overview:'Kiến thức tiểu đường'};
    const actions={PLAN_WORKFLOW:'Lập kế hoạch và chọn công cụ',VALIDATE_INPUT:'Kiểm tra đầu vào',INPUT_DECISION:'Xác nhận phạm vi xử lý',SELECT_ACTION:'Chọn bước thực thi',UNDERSTAND_QUERY:'Nhận diện nội dung câu hỏi',QUERY_TOPICS:'Xác định chủ đề',RETRIEVE_KNOWLEDGE:'Truy xuất tài liệu có nguồn',LOOKUP_GRAPH:'Tra cứu quan hệ đồ thị',VALIDATE_EVIDENCE:'Kiểm chứng bằng chứng',COMPOSE_EXTRACTIVE_RESPONSE:'Tổng hợp nội dung trả lời',VALIDATE_RESPONSE:'Kiểm tra phản hồi',RESPONSE_DECISION:'Xác nhận phản hồi',RESPOND_CONVERSATION:'Trả lời giao tiếp',RUN_PREDICTION:'Gọi mô hình dự đoán',VALIDATE_PREDICTION:'Kiểm tra kết quả mô hình'};
    const senders={Coordinator:'Điều phối',Knowledge:'Tri thức',Safety:'Kiểm chứng',Prediction:'Dự đoán'};
    const outcomes={ANSWERED:'Đã trả lời',REQUEST_INFO:'Cần thêm thông tin',NO_EVIDENCE:'Chưa đủ bằng chứng',ESCALATE:'Cần hỗ trợ chuyên môn',TOOL_OR_BUDGET_ERROR:'Chưa hoàn thành'};
    const number=(value,digits=1)=>Number(value).toLocaleString('vi-VN',{minimumFractionDigits:digits,maximumFractionDigits:digits});
    const el=(tag,className,text)=>{const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=text;return n;};

    async function api(path,options={}){
        const method=options.method||'GET',headers={Accept:'application/json'};
        if(options.body!==undefined)headers['Content-Type']='application/json';
        if(method!=='GET')headers['X-CSRF-Token']=csrf;
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);
        try{
            const response=await fetch(path,{method,headers,credentials:'same-origin',signal:controller.signal,...(options.body!==undefined?{body:JSON.stringify(options.body)}:{})});
            let data;
            try{data=await response.json();}catch{throw new Error('Máy chủ chưa trả về dữ liệu hợp lệ. Vui lòng thử lại.');}
            if(!response.ok||data.success===false)throw new Error(data.error||'Không thể hoàn thành yêu cầu.');
            return data;
        }catch(error){
            if(error.name==='AbortError')throw new Error('Kết nối đã hết thời gian chờ. Bạn có thể mở lại cuộc trò chuyện từ lịch sử.');
            throw error;
        }finally{clearTimeout(timer);}
    }
    function showError(message){$('chatError').textContent=message;$('chatError').hidden=!message;}
    function updateControls(){
        $('sendMessage').disabled=!ready||busy;$('chatInput').disabled=busy;
        $('newConversation').disabled=busy;$('conversationSelect').disabled=busy;
        $('clearHistory').disabled=busy||$('conversationSelect').options.length<=1;
        document.querySelectorAll('#suggestedQueries button').forEach(button=>{button.disabled=!ready||busy;});
        $('chatPanel').setAttribute('aria-busy',String(busy));
    }
    function sourceLink(url,label){
        const anchor=el('a','',label);
        try{const parsed=new URL(url);if(parsed.protocol==='https:'&&['www.niddk.nih.gov','www.cdc.gov','www.medlineplus.gov','medlineplus.gov','diabetes.org','www.nhs.uk','www.canada.ca','www.diabetes.org.uk','www.nccih.nih.gov'].includes(parsed.hostname))anchor.href=parsed.href;}catch{}
        anchor.target='_blank';anchor.rel='noopener noreferrer';return anchor;
    }
    function row(role){
        const wrapper=el('article','assistant-message '+role),avatar=el('span','message-avatar');
        avatar.setAttribute('aria-hidden','true');avatar.append(el('i',role==='user'?'fa-regular fa-user':'fa-solid fa-stethoscope'));
        const content=el('div','message-content');content.append(el('div','message-role',role==='user'?'Bạn':'Trợ lý tiểu đường'));
        const bubble=el('div','message-bubble');content.append(bubble);wrapper.append(avatar,content);
        return{wrapper,content,bubble};
    }
    function addUser(message){const r=row('user');r.bubble.append(el('p','',message));$('chatMessages').append(r.wrapper);}
    function welcome(){
        const r=row('assistant');r.bubble.append(el('p','','Chào bạn! Tôi có thể hỗ trợ tìm hiểu về tiểu đường, dinh dưỡng, vận động và các xét nghiệm.'),el('p','','Bạn muốn hỏi điều gì?'));
        $('chatMessages').append(r.wrapper);
    }
    function scrollChat(){$('chatMessages').scrollTop=$('chatMessages').scrollHeight;}
    function addAssistant(task){
        const r=row('assistant');r.wrapper.dataset.taskId=task.task_id;
        if(task.outcome!=='ANSWERED')r.bubble.append(el('div','message-notice '+(task.status==='FAILED'||task.outcome==='ESCALATE'?'is-error':''),outcomes[task.outcome]||task.status));
        // Derive the heading from the stored classification, including older
        // replies whose prose never explained what label 0/1 means.
        if(task.outcome==='ANSWERED'&&task.prediction&&[0,1].includes(task.prediction.label)){
            const result=el('div','message-prediction-result');
            result.append(el('span','message-prediction-caption','Kết quả dự đoán của mô hình'),
                el('strong','message-prediction-verdict',task.prediction.label===1?'Có tiểu đường':'Không tiểu đường'),
                el('small','','Phân loại tham khảo trong nghiên cứu, chưa phải chẩn đoán xác nhận.'));
            r.bubble.append(result);
        }
        if(task.reply)r.bubble.append(el('p','',task.reply));
        const blocks=task.answer_blocks||task.blocks||[];
        blocks.forEach(block=>{
            const p=el('p','',block.text);
            (block.evidence_ids||[]).forEach(id=>{const hit=(task.evidence||[]).find(h=>h.doc_id===id);if(hit){const link=sourceLink(hit.source_url,'['+id+'] ↗');link.className='message-citation';p.append(link);}});
            r.bubble.append(p);
        });
        if(!task.reply&&!blocks.length)(task.reasons||['Chưa có thông tin phù hợp để trả lời.']).forEach(reason=>r.bubble.append(el('p','',reason)));
        if((task.evidence||[]).length){
            const details=el('details','message-sources');details.append(el('summary','','Nguồn tham khảo ('+task.evidence.length+')'));
            task.evidence.forEach(hit=>{const item=el('div','message-source');item.append(sourceLink(hit.source_url,hit.doc_id+' · '+hit.title+' ↗'),el('small','',(hit.publisher||'Nguồn y tế')+' · Tóm tắt tiếng Việt'));details.append(item);});
            r.bubble.append(details);
        }
        const inspect=el('button','message-inspect','Xem luồng xử lý · '+number(task.latency_ms,2)+' ms');
        inspect.type='button';inspect.addEventListener('click',()=>renderFlow(task));r.content.append(inspect);
        $('chatMessages').append(r.wrapper);
    }
    function flowNode(name,active,warning=false){const n=$('flow-'+name);n.classList.toggle('is-active',Boolean(active));n.classList.toggle('is-warning',Boolean(warning));}
    function edge(name,active){$('edge-'+name).classList.toggle('is-active',Boolean(active));}
    function clearFlow(){
        ['input','coordinator','rag','graph','model','safety','response'].forEach(n=>flowNode(n,false));
        ['input','rag','graph','model','rag-check','graph-check','model-check','response'].forEach(n=>edge(n,false));
        $('runState').textContent='Chờ tin nhắn';$('runState').className='assistant-small-badge';
        $('planReason').textContent='Gửi một tin nhắn để xem công cụ nào được chọn và lý do lựa chọn.';
        $('planSteps').replaceChildren(el('li','plan-placeholder','Chưa có yêu cầu đang chọn.'));
        $('contextBadge').hidden=true;$('traceCount').textContent='0 sự kiện';
        $('executionTrace').replaceChildren(el('li','','Nhật ký xuất hiện khi yêu cầu được xử lý.'));
        document.querySelectorAll('[data-tool]').forEach(n=>{n.classList.remove('is-used');n.querySelector('b').textContent=n.dataset.tool==='model'?'Chưa cần':'Chưa gọi';});
        $('latencyMetric').textContent='Thời gian: —';$('callsMetric').textContent='Công cụ: —';$('sourcesMetric').textContent='Nguồn: —';
        document.querySelectorAll('.assistant-message.is-selected').forEach(n=>n.classList.remove('is-selected'));
    }
    Object.assign(topics,{type2:'Tiểu đường tuýp 2',type1:'Tiểu đường tuýp 1',prediabetes:'Tiền tiểu đường',pregnancy:'Thai kỳ',alcohol:'Rượu bia',juice:'Nước ép và đồ uống',rice:'Tinh bột',fruit:'Trái cây và thực phẩm',feet:'Bàn chân',eyes:'Sức khỏe mắt',nerves:'Thần kinh',heart:'Tim mạch',dental:'Răng miệng',cgm:'Theo dõi glucose',sickdays:'Chăm sóc khi ốm',dka:'Nhiễm toan ceton',travel:'Đi xa',mental:'Sức khỏe tinh thần',heat:'Nắng nóng',medicine_types:'Thông tin thuốc',sleep:'Giấc ngủ',supplements:'Chất bổ sung',sexual:'Sinh lý và bàng quang',kidney_damage:'Bảo vệ thận',plate:'Lập bữa ăn',labels:'Nhãn thực phẩm',exercise_safety:'Vận động an toàn',diagnostic_thresholds:'Ngưỡng xét nghiệm',remission:'Thuyên giảm',inheritance:'Di truyền và nguyên nhân',metformin:'Metformin',contagion:'Khả năng lây nhiễm'});
    topics.prediction='Phân loại bằng mô hình';
    outcomes.OUT_OF_SCOPE='Ngoài phạm vi mô hình';
    actions.COLLECT_PREDICTION_INPUTS='Thu thập và kiểm tra chỉ số';
    actions.EXPLAIN_PREDICTION_RESULT='Giải thích kết quả dự đoán đã có';
    actions.COMPOSE_ASSISTED_RESPONSE='Diễn đạt câu trả lời từ bằng chứng';
    function renderFlow(task){
        const trace=task.trace||[],called=action=>trace.some(e=>e.action===action&&e.status!=='FAILED');
        const rag=called('RETRIEVE_KNOWLEDGE'),graph=called('LOOKUP_GRAPH'),model=called('RUN_PREDICTION'),safety=trace.some(e=>e.sender==='Safety');
        flowNode('input',true);flowNode('coordinator',true);flowNode('rag',rag);flowNode('graph',graph);flowNode('model',model);
        flowNode('safety',safety,task.safety_status!=='ALLOW');flowNode('response',true,task.status==='FAILED');
        edge('input',true);edge('rag',rag);edge('graph',graph);edge('model',model);
        edge('rag-check',rag);edge('graph-check',graph);edge('model-check',model);edge('response',true);
        $('runState').textContent=outcomes[task.outcome]||task.status;
        $('runState').className='assistant-small-badge '+(task.outcome==='ANSWERED'?'is-active':'is-warning');
        const plan=task.plan||{};
        $('planReason').textContent=plan.reason||'Luồng hiển thị được tổng hợp từ nhật ký thực thi của tin nhắn này.';
        $('contextBadge').hidden=!plan.uses_context;
        $('planSteps').replaceChildren(...(plan.steps||['Tiếp nhận yêu cầu','Truy xuất thông tin','Kiểm chứng và phản hồi']).map(step=>el('li','',step)));
        document.querySelectorAll('[data-tool]').forEach(n=>{const used={rag,graph,model}[n.dataset.tool];n.classList.toggle('is-used',used);n.querySelector('b').textContent=used?'Đã gọi':'Chưa cần';});
        $('executionTrace').replaceChildren();
        trace.forEach(e=>{
            const item=el('li',e.status==='FAILED'?'is-failed':'');
            item.append(el('strong','',senders[e.sender]||e.sender),document.createTextNode(' · '+(actions[e.action]||e.action)));
            const labels=e.payload?.topics||[];
            item.append(el('small','',number(e.duration_ms,2)+' ms'+(labels.length?' · '+labels.map(t=>topics[t]||t).join(', '):'')+(e.status==='FAILED'?' · có lỗi':'')));
            $('executionTrace').append(item);
        });
        $('traceCount').textContent=trace.length+' sự kiện';$('latencyMetric').textContent='Thời gian: '+number(task.latency_ms,2)+' ms';
        $('callsMetric').textContent='Công cụ: '+task.tool_calls;$('sourcesMetric').textContent='Nguồn: '+(task.evidence||[]).length;
        document.querySelectorAll('.assistant-message[data-task-id]').forEach(n=>n.classList.toggle('is-selected',n.dataset.taskId===task.task_id));
    }
    function newConversation(){conversationId=null;$('chatMessages').replaceChildren();welcome();clearFlow();$('conversationSelect').value='';$('chatInput').value='';showError('');$('chatStatus').textContent='Sẵn sàng';updateControls();}
    async function refreshConversations(){
        const data=await api('/api/v1/assistant/conversations');
        const initial=el('option','','Cuộc trò chuyện mới');initial.value='';$('conversationSelect').replaceChildren(initial);
        data.conversations.forEach(c=>{const option=el('option','',c.title);option.value=c.conversation_id;$('conversationSelect').append(option);});
        $('conversationSelect').value=conversationId||'';updateControls();return data.conversations;
    }
    async function loadConversation(id){
        if(!id){newConversation();return;}
        busy=true;updateControls();showError('');
        try{
            const data=await api('/api/v1/assistant/conversations/'+encodeURIComponent(id));conversationId=id;
            $('chatMessages').replaceChildren();welcome();data.tasks.forEach(t=>{addUser(t.query);addAssistant(t);});
            if(data.tasks.length)renderFlow(data.tasks[data.tasks.length-1]);else clearFlow();
            $('chatStatus').textContent='Đã mở lại';$('conversationSelect').value=id;scrollChat();
        }catch(error){showError(error.message);}finally{busy=false;updateControls();}
    }
    async function send(){
        if(!ready||busy)return;
        const message=$('chatInput').value.trim();if(!message){$('chatInput').focus();return;}
        showError('');busy=true;updateControls();clearFlow();
        $('runState').textContent='Đang tiếp nhận';$('runState').classList.add('is-active');flowNode('input',true);
        $('planReason').textContent='Đang xử lý tin nhắn. Các bước thực thi sẽ xuất hiện khi có phản hồi.';
        $('chatStatus').textContent='Đang trả lời';addUser(message);$('chatInput').value='';
        const pending=row('assistant');pending.bubble.append(el('span','message-pending','Đang tìm thông tin cho bạn…'));$('chatMessages').append(pending.wrapper);scrollChat();
        try{
            const body={message};if(conversationId)body.conversation_id=conversationId;
            const data=await api('/api/v1/assistant/chat',{method:'POST',body});
            pending.wrapper.remove();conversationId=data.conversation_id;addAssistant(data.task);renderFlow(data.task);
            $('chatStatus').textContent=outcomes[data.task.outcome]||'Đã xử lý';scrollChat();
            try{await refreshConversations();}catch{showError('Đã có phản hồi, nhưng chưa tải lại được danh sách trò chuyện.');}
        }catch(error){
            pending.wrapper.remove();const failure=row('assistant');failure.bubble.append(el('p','',error.message));$('chatMessages').append(failure.wrapper);
            showError(error.message);$('chatStatus').textContent='Cần thử lại';$('runState').textContent='Chưa hoàn thành';scrollChat();
        }finally{busy=false;updateControls();$('chatInput').focus();}
    }
    $('chatForm').addEventListener('submit',event=>{event.preventDefault();send();});
    $('chatInput').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();send();}});
    $('newConversation').addEventListener('click',()=>{newConversation();$('chatInput').focus();});
    $('conversationSelect').addEventListener('change',()=>loadConversation($('conversationSelect').value));
    $('clearHistory').addEventListener('click',async()=>{
        if(busy)return;busy=true;updateControls();
        try{await api('/api/v1/assistant/conversations',{method:'DELETE'});newConversation();await refreshConversations();}
        catch(error){showError(error.message);}finally{busy=false;updateControls();}
    });
    async function boot(){
        welcome();clearFlow();
        try{
            const setup=await api('/api/v1/agents/session');csrf=setup.csrf_token;
            const suggestions=[['Ăn uống','Tiểu đường ăn được gì'],['Theo dõi A1C','A1C cho biết điều gì trong kế hoạch chăm sóc?'],['Vận động','Hoạt động thể chất có vai trò gì?'],['Xét nghiệm','Làm sao biết có bị tiểu đường không?'],['Đánh giá bằng chỉ số','Tôi muốn đánh giá nguy cơ tiểu đường bằng các chỉ số sức khỏe'],['Thử dữ liệu mẫu','Chạy thử dự đoán bằng dữ liệu mẫu']];
            suggestions.forEach(([label,query])=>{const button=el('button','',label);button.type='button';button.title=query;button.addEventListener('click',()=>{$('chatInput').value=query;send();});$('suggestedQueries').append(button);});
            const health=await api('/api/v1/health');ready=true;$('serviceBadge').textContent='● Hệ thống sẵn sàng';$('serviceBadge').classList.add('is-ready');
            const stats=health.knowledge_graph;
            if(stats)$('knowledgeStats').textContent=stats.documents+' tài liệu · '+stats.clinical_entities+' thực thể · '+stats.clinical_relations+' quan hệ có nguồn';
            const conversations=await refreshConversations();if(conversations.length)await loadConversation(conversations[0].conversation_id);
        }catch(error){showError(error.message);$('serviceBadge').textContent='Chưa kết nối được';$('serviceBadge').classList.add('is-error');}
        finally{updateControls();}
    }
    boot();
})();
