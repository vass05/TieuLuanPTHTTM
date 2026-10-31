"""Check canvas and upload inference with the real saved model in Chrome/Edge."""
import json
import socket
import subprocess
import time
import uuid
import base64

from check_agents_browser import Browser,CHROME,HTTP,OUT,ROOT,EXCEPTIONS


def main():
    if CHROME is None:raise RuntimeError('Chrome or Edge is required')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    profile=ROOT/'.ipynb_checkpoints'/('chrome-vision-'+uuid.uuid4().hex)
    process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run',
        '--no-default-browser-check','--remote-debugging-port='+str(port),'--window-size=1440,1100',
        '--user-data-dir='+str(profile),'about:blank'],stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    browser=None;checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name);print('PASS',name,flush=True)
    try:
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                tab=next(t for t in HTTP.get(f'http://127.0.0.1:{port}/json/list',timeout=1).json() if t.get('type')=='page')
                break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('Browser did not start')
        browser=Browser(tab['webSocketDebuggerUrl'])
        browser.call('Runtime.enable');browser.call('Page.enable');browser.call('Network.enable')
        browser.call('Network.setBlockedURLs',{'urls':['https://cdn.jsdelivr.net/npm/chart.js*']})
        check('vision_page_returns_200',HTTP.get('http://127.0.0.1:5000/vision',timeout=15).status_code==200)
        browser.call('Page.navigate',{'url':'http://127.0.0.1:5000/vision'})
        browser.wait("typeof recognize==='function' && typeof bootstrap!=='undefined'",seconds=45)
        browser.js("""window.visionAlerts=[];window.alert=message=>visionAlerts.push(message);
            window.visionResponses=[];window.visionFetch=window.fetch;
            window.fetch=async (...args)=>{const r=await window.visionFetch(...args);if(String(args[0])==='/api/vision/predict')visionResponses.push({status:r.status,data:await r.clone().json()});return r;};
            const c=document.getElementById('paintCanvas'),p=c.getContext('2d');
            p.fillStyle='white';p.fillRect(0,0,c.width,c.height);p.fillStyle='black';
            p.fillRect(60,100,160,140);p.lineWidth=15;p.strokeStyle='black';p.beginPath();p.arc(140,100,45,Math.PI,0);p.stroke();""")
        check('canvas_request_disables_buttons_while_running',browser.js("document.getElementById('btnPredictCanvas').click();document.getElementById('btnPredictCanvas').disabled && document.getElementById('btnPredictUpload').disabled"))
        browser.wait("visionResponses.length===1 && !document.getElementById('btnPredictCanvas').disabled")
        check('canvas_inference_returns_200_instead_of_503',browser.js("visionResponses[0].status===200 && visionResponses[0].data.success"))
        check('top_class_and_five_probabilities_are_rendered',browser.js("document.getElementById('topLabelVi').textContent===visionResponses[0].data.result.top_label_vi && document.querySelectorAll('#probBarsContainer .progress-bar').length===5 && document.getElementById('visionError').hidden"))
        browser.screenshot('vision_canvas_fixed.png')
        browser.js("document.getElementById('tabUpload').click()")
        browser.wait("document.getElementById('paneUpload').classList.contains('active')")
        check('upload_tab_opens',browser.js("!document.getElementById('tabDraw').classList.contains('active')"))
        browser.js("""(async()=>{const blob=await new Promise(resolve=>document.getElementById('paintCanvas').toBlob(resolve,'image/png'));const dt=new DataTransfer();dt.items.add(new File([blob],'test-sketch.png',{type:'image/png'}));const input=document.getElementById('imageFileInput');input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));})()""")
        browser.wait("!document.getElementById('previewContainer').classList.contains('d-none')")
        check('uploaded_file_preview_is_visible',browser.js("document.getElementById('fileNameBadge').textContent.includes('test-sketch.png')"))
        browser.js("document.getElementById('btnPredictUpload').click()")
        browser.wait("visionResponses.length===2 && !document.getElementById('btnPredictUpload').disabled")
        check('upload_inference_matches_canvas',browser.js("visionResponses[1].status===200 && JSON.stringify(visionResponses[0].data.result)===JSON.stringify(visionResponses[1].data.result)"))
        browser.screenshot('vision_upload_fixed.png')
        browser.js("document.getElementById('visionTask').value='digits';document.getElementById('visionTask').dispatchEvent(new Event('change'))")
        check('digit_mode_has_its_own_hint_and_resets_fashion_result',browser.js("document.getElementById('topConfidence').textContent==='--%' && document.getElementById('drawHint').textContent.includes('0') && document.getElementById('visionAccuracy').textContent.includes('MNIST') && document.querySelectorAll('#probBarsContainer .progress-bar').length===0"))
        browser.js("document.getElementById('tabDraw').click();const digitPen=document.getElementById('paintCanvas').getContext('2d');digitPen.fillStyle='white';digitPen.fillRect(0,0,280,280);digitPen.strokeStyle='black';digitPen.lineWidth=18;digitPen.lineCap='round';digitPen.beginPath();digitPen.moveTo(90,70);digitPen.bezierCurveTo(210,30,215,135,130,140);digitPen.bezierCurveTo(240,140,220,250,85,225);digitPen.stroke();document.getElementById('btnPredictCanvas').click()")
        browser.wait("visionResponses.length===3 && !document.getElementById('btnPredictCanvas').disabled")
        check('handwritten_three_uses_digit_model',browser.js("visionResponses[2].status===200 && visionResponses[2].data.result.task==='digits' && visionResponses[2].data.result.digit===3"))
        check('digit_top_five_has_digit_labels',browser.js("document.getElementById('topLabelVi').textContent==='Số 3' && visionResponses[2].data.result.ranking.every(row=>row.label_en.startsWith('Digit '))"))
        browser.wait("getComputedStyle(document.getElementById('paneDraw')).opacity==='1'")
        browser.screenshot('vision_digit_canvas.png')
        encoded=base64.b64encode((ROOT/'tests/fixtures/digits/7.png').read_bytes()).decode('ascii')
        browser.js("document.getElementById('tabUpload').click();const digitBytes=Uint8Array.from(atob("+json.dumps(encoded)+"),c=>c.charCodeAt(0));const digitFiles=new DataTransfer();digitFiles.items.add(new File([digitBytes],'digit-7.png',{type:'image/png'}));document.getElementById('imageFileInput').files=digitFiles.files;document.getElementById('imageFileInput').dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('btnPredictUpload').click()")
        browser.wait("visionResponses.length===4 && !document.getElementById('btnPredictUpload').disabled")
        check('uploaded_seven_uses_digit_model',browser.js("visionResponses[3].status===200 && visionResponses[3].data.result.digit===7 && document.getElementById('topLabelVi').textContent==='Số 7'"))
        browser.wait("getComputedStyle(document.getElementById('paneUpload')).opacity==='1'")
        browser.screenshot('vision_digit_upload.png')
        browser.js("document.getElementById('tabDraw').click();document.getElementById('btnClearCanvas').click();document.getElementById('btnPredictCanvas').click()")
        browser.wait("visionResponses.length===5 && !document.getElementById('btnPredictCanvas').disabled")
        check('blank_digit_canvas_returns_input_error_without_a_prediction',browser.js("visionResponses[4].status===400 && !document.getElementById('visionError').hidden && document.getElementById('topConfidence').textContent==='--%'"))
        browser.js("document.getElementById('visionTask').value='fashion';document.getElementById('visionTask').dispatchEvent(new Event('change'));document.getElementById('tabUpload').click()")
        check('switching_back_restores_fashion_configuration',browser.js("document.getElementById('visionAccuracy').textContent.includes('91.67') && document.getElementById('topConfidence').textContent==='--%'"))
        browser.js("window.fetch=async()=>new Response(JSON.stringify({success:false,error:'Mô hình nhận diện chưa sẵn sàng. Hãy thử lại.'}),{status:503,headers:{'Content-Type':'application/json'}});document.getElementById('btnPredictUpload').click()")
        browser.wait("!document.getElementById('btnPredictUpload').disabled && !document.getElementById('visionError').hidden")
        check('model_error_is_explained_inline',browser.js("document.getElementById('visionError').textContent.includes('Mô hình nhận diện chưa sẵn sàng') && !document.getElementById('btnPredictCanvas').disabled"))
        browser.js("window.fetch=window.visionFetch;document.getElementById('btnRemoveImg').click();document.getElementById('btnPredictUpload').click()")
        check('missing_file_is_explained_inline',browser.js("!document.getElementById('visionError').hidden && document.getElementById('visionError').textContent.includes('chọn một tệp')"))
        check('no_error_popup_was_shown',browser.js("visionAlerts.length===0"))
        check('desktop_has_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth"))
        browser.call('Emulation.setDeviceMetricsOverride',dict(width=390,height=844,deviceScaleFactor=1,mobile=True))
        check('mobile_has_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth"))
        check('no_browser_javascript_exceptions',not EXCEPTIONS)
        (OUT/'vision_browser_checks.json').write_text(json.dumps(dict(checks=checks,passed=len(checks),exceptions=EXCEPTIONS),indent=2),encoding='utf-8')
    finally:
        if browser:browser.socket.close()
        process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
