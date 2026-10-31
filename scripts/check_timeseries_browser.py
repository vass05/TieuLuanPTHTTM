"""Check the real forecast page, Chart.js and AJAX with a private browser profile."""
import json
import socket
import subprocess
import time
import uuid

from check_agents_browser import Browser, CHROME, HTTP, OUT, ROOT, EXCEPTIONS


def main():
    if CHROME is None:
        raise RuntimeError('Chrome or Edge is required')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0))
        port=listener.getsockname()[1]
    profile=ROOT/'.ipynb_checkpoints'/('chrome-timeseries-'+uuid.uuid4().hex)
    process=subprocess.Popen([str(CHROME),'--headless=new','--disable-gpu','--no-first-run',
        '--no-default-browser-check','--remote-debugging-port='+str(port),
        '--window-size=1440,1100','--user-data-dir='+str(profile),'about:blank'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    browser=None
    checks=[]
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
        browser.call('Runtime.enable');browser.call('Page.enable')
        browser.call('Network.enable')
        # This page needs Chart.js, but does not use the Bootstrap JS bundle.
        browser.call('Network.setBlockedURLs',{'urls':['https://cdn.jsdelivr.net/npm/bootstrap@*/dist/js/*']})
        response=HTTP.get('http://127.0.0.1:5000/timeseries',timeout=20)
        check('timeseries_returns_200',response.status_code==200)
        browser.call('Page.navigate',{'url':'http://127.0.0.1:5000/timeseries'})
        browser.wait("typeof Chart!=='undefined' && Boolean(Chart.getChart('stockChart'))",seconds=45)
        check('real_chart_renders',browser.js("Chart.getChart('stockChart').data.datasets.length===2"))
        check('initial_table_has_seven_predictions',browser.js("document.querySelectorAll('#forecastTableBody tr').length===7"))
        check('chart_has_saved_model_prediction',browser.js("Chart.getChart('stockChart').data.datasets[1].data.includes(134.53)"))
        browser.js("Chart.getChart('stockChart').stop();Chart.getChart('stockChart').update('none')")
        browser.screenshot('timeseries_fixed.png')
        browser.js("document.getElementById('stepsSelect').value='14';document.getElementById('forecastForm').dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}))")
        browser.wait("document.querySelectorAll('#forecastTableBody tr').length===14 && !document.getElementById('btnSubmit').disabled")
        check('ajax_updates_to_fourteen_predictions',browser.js("Chart.getChart('stockChart').data.labels.length===74"))
        check('desktop_has_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth"))
        browser.call('Emulation.setDeviceMetricsOverride',dict(width=390,height=844,deviceScaleFactor=1,mobile=True))
        check('mobile_has_no_horizontal_overflow',browser.js("document.documentElement.scrollWidth<=innerWidth"))
        check('no_browser_javascript_exceptions',not EXCEPTIONS)
        (OUT/'timeseries_browser_checks.json').write_text(json.dumps(dict(checks=checks,passed=len(checks),exceptions=EXCEPTIONS),indent=2),encoding='utf-8')
    finally:
        if browser:browser.socket.close()
        process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
