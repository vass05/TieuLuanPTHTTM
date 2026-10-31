"""Deterministic collection of model inputs in chat; never invent missing labs."""
import copy
import math
import re
import unicodedata

from mvc.models.diabetes_dialogue import normalize_question

FIELDS = {
    'Age': ('Tuổi', ['age','tuoi'], 'years'),
    'Pregnancies': ('Số lần mang thai', ['pregnancies','so lan mang thai','mang thai'], 'count'),
    'Glucose': ('Glucose sau 2 giờ OGTT', ['glucose sau 2 gio ogtt','duong huyet sau 2 gio ogtt','glucose','duong huyet'], 'mg/dL'),
    'BloodPressure': ('Huyết áp tâm trương', ['bloodpressure','huyet ap tam truong','tam truong'], 'mmHg'),
    'SkinThickness': ('Độ dày nếp gấp da', ['skinthickness','do day nep gap da','nep gap da','do day da'], 'mm'),
    'Insulin': ('Insulin huyết thanh sau 2 giờ', ['insulin huyet thanh sau 2 gio','insulin huyet thanh','insulin'], 'uU/mL'),
    'BMI': ('BMI', ['bmi','chi so khoi co the'], 'kg/m2'),
    'DiabetesPedigreeFunction': ('Chỉ số phả hệ tiểu đường (DPF)', ['diabetespedigreefunction','chi so pha he tieu duong','chi so pha he','dpf'], 'score'),
}
NUMBER = r'[-+]?(?:\d+(?:[.,]\d+)?|\.\d+)(?:e[-+]?\d+)?'
UNIT_PATTERNS = [
    (r'\bmmol\s*/\s*l\b','mmol/L'), (r'\bmg\s*/\s*dl\b','mg/dL'),
    (r'(?:\b(?:u|micro)u|µu|μu)\s*/\s*ml\b','uU/mL'),
    (r'\bmmhg\b','mmHg'), (r'\bkg\s*/\s*m(?:2|²)\b','kg/m2'),
    (r'\bmm\b','mm'), (r'\bcm\b','cm'), (r'\b(?:iu|don vi)\b','IU'),
]


def fold(text):
    text=unicodedata.normalize('NFD',text.lower().replace('đ','d'))
    return ''.join(c for c in text if unicodedata.category(c)!='Mn')


def parse_inputs(message):
    text=fold(message)
    values,units,issues,invalid={}, {}, [], set()
    locations=[]
    glucose_segments=[]
    for key,(_,aliases,_) in FIELDS.items():
        pattern=r'(?<!\w)(?:'+'|'.join(re.escape(a) for a in sorted(aliases,key=len,reverse=True))+r')(?!\w)'
        for match in re.finditer(pattern,text):
            locations.append((match.start(),match.end(),key))
    locations.sort()
    for index,(start,end,key) in enumerate(locations):
        stop=locations[index+1][0] if index+1<len(locations) else len(text)
        segment=text[end:stop]
        if key=='Glucose':glucose_segments.append(text[start:stop])
        value=re.match(r'\s*(?:[:=]|la)?\s*('+NUMBER+r')(?![\d.,]|e[-+]?\d)',segment)
        for pattern,unit in UNIT_PATTERNS:
            if re.search(pattern,segment):
                units[key]=unit
                break
        if value:
            number=float(value[1].replace(',','.'))
            if key in values and values[key]!=number:
                issues.append('Bạn nhập hai giá trị khác nhau cho '+FIELDS[key][0]+'. Hãy gửi lại một giá trị rõ ràng.')
                invalid.add(key)
                values.pop(key,None)
            elif not math.isfinite(number) or abs(number)>3.4e38:
                issues.append(FIELDS[key][0]+': giá trị không hợp lệ.')
                invalid.add(key)
            else:
                values[key]=number
        elif re.match(r'\s*[:=]\s*(?:nan|inf|[a-z]+)',segment) and key not in units:
            invalid.add(key)
            issues.append(FIELDS[key][0]+': cần nhập một số hợp lệ.')
    # Conversational age order: "tôi 47 tuổi". Do not map bare numbers to labs.
    if 'Age' not in values:
        age=re.search(r'(?<![\w.])('+NUMBER+r')\s*tuoi\b',text)
        if age:
            number=float(age[1].replace(',','.'))
            if math.isfinite(number):values['Age']=number
    if re.search(r'\b(?:chua tung|chua lan nao) mang thai\b',text):
        values['Pregnancies']=0
    if re.search(r'\bhuyet ap\s*[:=]?\s*(\d+)\s*/\s*(\d+)\s*mmhg\b',text):
        bp=re.search(r'\bhuyet ap\s*[:=]?\s*(\d+)\s*/\s*(\d+)\s*mmhg\b',text)
        values['BloodPressure']=float(bp[2]);units['BloodPressure']='mmHg'
    sex=None
    if re.search(r'\b(?:nu|phu nu|female)\b',text):sex='female'
    if re.search(r'\b(?:gioi tinh nam|nam gioi|toi(?: la)? nam|male)\b',text) or text.strip()=='nam':sex='male'
    sex_unknown=bool(re.search(r'\b(?:khong|chua)\b.{0,15}\b(?:nu|phu nu|gioi tinh)\b',text))
    if sex_unknown:sex=None
    glucose_text=' '.join(glucose_segments) if glucose_segments else '' if locations else text
    fasting=bool(re.search(r'\b(?:luc doi|khi doi|fasting)\b',glucose_text))
    ogtt=bool(re.search(r'\b(?:ogtt|nghiem phap dung nap)\b',glucose_text) and re.search(r'\b(?:2|hai)\s*(?:gio|h)\b',glucose_text)
        and not re.search(r'\b(?:khong|chua)\b.{0,40}\b(?:ogtt|nghiem phap)\b',glucose_text))
    return dict(values=values,units=units,issues=issues,invalid=invalid,sex=sex,sex_unknown=sex_unknown,fasting=fasting,ogtt=ogtt)


def prediction_request(message,previous,examples):
    normalized=normalize_question(message)
    last=previous[-1].get('_prediction_dialogue') if previous else None
    pending=bool(last and last.get('active'))
    cancel=any(p in normalized for p in ('huy du doan','dung du doan','ngung du doan','huy danh gia','khong du doan nua')) or normalized=='dung lai'
    explicit=any(p in normalized for p in ('danh gia nguy co','du doan nguy co','du doan tieu duong',
        'du doan dai thao duong','kiem tra nguy co','chay mo hinh','phan tich chi so',
        'danh gia bang chi so','du doan bang chi so','chay thu du doan','tiep tuc du doan'))
    educational=any(p in normalized for p in ('mo hinh la gi','mo hinh du doan la gi','hoat dong the nao'))
    demo=explicit and any(p in normalized for p in ('du lieu mau','ho so mau','vi du mau'))
    parsed=parse_inputs(message)
    continuation=pending and (bool(parsed['values'] or parsed['units'] or parsed['sex'] or parsed['sex_unknown'] or parsed['invalid'] or parsed['ogtt']) or
        any(p in normalized for p in ('khong biet','khong co chi so','khong co ket qua','tiep tuc','thu lai')))
    if not (cancel and pending) and not (explicit and not educational) and not continuation:
        return None
    state=copy.deepcopy(last) if pending else dict(profile={},units={},sex=None,ogtt=False,active=True,demo=False)
    if cancel:
        state['active']=False
        return dict(state=state,ready=False,outcome='ANSWERED',missing=[],issues=[],
            reply='Đã hủy thu thập chỉ số. Bạn có thể tiếp tục hỏi về tiểu đường hoặc bắt đầu yêu cầu dự đoán mới.')
    if demo:
        state=dict(profile=copy.deepcopy(examples[0]['profile']),units={k:v[2] for k,v in FIELDS.items()},
            sex='female',ogtt=True,active=True,demo=True)
    else:
        state['profile'].update(parsed['values']);state['units'].update(parsed['units'])
        for key in parsed['invalid']:state['profile'].pop(key,None)
        if parsed['sex']:state['sex']=parsed['sex']
        elif parsed['sex_unknown']:state['sex']=None
        if parsed['fasting']:state['ogtt']=False
        elif parsed['ogtt']:state['ogtt']=True
        # A new glucose number must have a stated measurement context.
        elif 'Glucose' in parsed['values']:state['ogtt']=False
        for key in parsed['values']:
            if key in {'Age','Pregnancies','DiabetesPedigreeFunction','BMI'}:
                state['units'].setdefault(key,FIELDS[key][2])
            elif key not in parsed['units']:
                state['units'].pop(key,None)
        # Do not silently mix a demo profile with a personal correction.
        if state.get('demo') and (parsed['values'] or parsed['sex']):
            state=dict(profile=parsed['values'],units=parsed['units'],sex=parsed['sex'],
                ogtt=parsed['ogtt'],active=True,demo=False)
    profile=state['profile']
    if state['sex']=='male' or ('Age' in profile and profile['Age']<21):
        state['active']=False
        return dict(state=state,ready=False,outcome='OUT_OF_SCOPE',missing=[],issues=[],
            reply='Mô hình hiện được huấn luyện từ bộ dữ liệu phụ nữ từ 21 tuổi, nên tôi không chạy dự đoán cho hồ sơ này. '
                'Bạn vẫn có thể hỏi về xét nghiệm hoặc gõ “Chạy thử dự đoán bằng dữ liệu mẫu” để xem cách mô hình hoạt động.')
    issues=list(parsed['issues']) if not demo else []
    missing=[]
    if not state['sex']:missing.append('Giới tính (phạm vi mô hình: nữ từ 21 tuổi)')
    for key,(label,_,expected_unit) in FIELDS.items():
        value=profile.get(key)
        if value is None:
            missing.append(label+(f' ({expected_unit})' if key not in {'Age','Pregnancies','DiabetesPedigreeFunction'} else ''))
            continue
        if (not math.isfinite(value) or value<0 or (key not in {'Pregnancies','DiabetesPedigreeFunction'} and value==0)
            or (key in {'Age','Pregnancies'} and value!=int(value))):
            issues.append(label+': cần giá trị hợp lệ; tuổi và số lần mang thai phải là số nguyên.')
        if state['units'].get(key)!=expected_unit:
            missing.append(label+': vui lòng ghi đơn vị '+expected_unit)
    if 'Glucose' in profile and not state['ogtt']:
        missing.append('Xác nhận glucose đo sau 2 giờ nghiệm pháp OGTT; không dùng glucose lúc đói thay thế')
    ready=not missing and not issues
    if ready:
        reply=None
    else:
        lines=['Tôi có thể chạy mô hình phân loại nghiên cứu khi có đủ dữ liệu phù hợp.']
        if profile:
            lines.append('Đã nhận: '+', '.join(FIELDS[k][0]+'='+format(v,'g') for k,v in profile.items())+'.')
        if issues:lines.extend(issues)
        if missing:lines.append('Cần bổ sung hoặc xác nhận:\n'+'\n'.join('• '+item for item in missing))
        lines.append('Bạn có thể gửi nhiều chỉ số trong một tin nhắn, ví dụ “Tôi là nữ, 47 tuổi, BMI=35,5”. '
            'DPF là chỉ số phả hệ có trong dữ liệu nghiên cứu, không phải câu trả lời có/không về người thân mắc bệnh. '
            'Không biết chỉ số nào thì không tự đoán; có thể gõ “Chạy thử dự đoán bằng dữ liệu mẫu”.')
        reply='\n\n'.join(lines)
    return dict(state=state,ready=ready,outcome='ANSWERED' if ready else 'REQUEST_INFO',missing=missing,issues=issues,reply=reply)


def prediction_reply(prediction,demo):
    return ('Kết quả chạy thử trên dữ liệu mẫu nghiên cứu.\n' if demo else 'Kết quả từ các chỉ số bạn cung cấp.\n')+(
        f"Điểm mô hình: {prediction['score']:.4f} trên thang 0–1. "
        f"Ngưỡng phân loại: {prediction['threshold']:.2f}. "
        f"Nhãn nghiên cứu: {prediction['label']} "
        f"({'đạt hoặc vượt' if prediction['label'] else 'dưới'} ngưỡng phân loại).\n"
        'Điểm này không phải xác suất chẩn đoán cá nhân và không xác nhận bạn có hay không mắc tiểu đường. '
        'Phần dưới là thông tin xét nghiệm để tham khảo.')
