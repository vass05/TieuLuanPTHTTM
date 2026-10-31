"""Latest-source routing must never silently substitute an archived CSV."""
from datetime import datetime, timezone

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from mvc.models.market_data import MarketData, MarketDataUnavailable


def frame(end='2026-10-30'):
    calendar=xcals.get_calendar('XNYS')
    days=calendar.sessions_in_range(pd.Timestamp(end)-pd.Timedelta(days=180),end)
    return pd.DataFrame({'Close':np.linspace(180,240.35,len(days))},index=days.tz_localize('America/New_York'))


@pytest.fixture
def market(tmp_path,monkeypatch):
    actual=MarketData(tmp_path)
    monkeypatch.setattr(actual,'_now',lambda:datetime(2026,10,31,12,tzinfo=timezone.utc))
    monkeypatch.setattr(actual,'_download',lambda _:frame())
    return actual


def test_latest_completed_session_and_source_are_preserved(market):
    result=market.history()
    assert result['last_date']=='2026-10-30' and result['last_price']==240.35
    assert len(result['dates'])==60 and len(result['prices'])==60
    assert result['source']=='live' and result['is_live']
    assert result['data_kind']=='daily_close' and result['timezone']=='America/New_York'
    assert result['source_url']=='https://finance.yahoo.com/quote/AMZN/history/'
    assert result['fetched_at'].startswith('2026-10-31')


def test_open_market_bar_is_excluded_and_cache_refreshes_when_session_closes(market,monkeypatch):
    calls=[]
    monkeypatch.setattr(market,'_download',lambda symbol:(calls.append(symbol) or frame()))
    monkeypatch.setattr(market,'_now',lambda:datetime(2026,10,30,15,tzinfo=timezone.utc))
    assert market.history()['last_date']=='2026-10-29'
    monkeypatch.setattr(market,'_now',lambda:datetime(2026,10,30,21,tzinfo=timezone.utc))
    assert market.history()['last_date']=='2026-10-30'
    assert calls==['AMZN','AMZN']


def test_half_day_market_close_uses_exchange_calendar(market,monkeypatch):
    monkeypatch.setattr(market,'_download',lambda _:frame('2026-11-27'))
    monkeypatch.setattr(market,'_now',lambda:datetime(2026,11,27,19,tzinfo=timezone.utc))
    assert market.history()['last_date']=='2026-11-27'  # 13:00 NY early close.


def test_cache_is_short_lived_and_returns_independent_values(market,monkeypatch):
    first=market.history()
    first['prices'][-1]=0
    monkeypatch.setattr(market,'_download',lambda _:pytest.fail('Fresh cache should avoid another request'))
    assert market.history()['last_price']==240.35
    assert market.history()['prices'][-1]==240.35


def test_expired_cache_does_not_hide_provider_failure(market,monkeypatch):
    market.history()
    stamp,data=market._cache[('AMZN',60)]
    market._cache[('AMZN',60)]=(stamp-301,data)
    def failure(_):raise TimeoutError('provider offline')
    monkeypatch.setattr(market,'_download',failure)
    with pytest.raises(MarketDataUnavailable):market.history()


@pytest.mark.parametrize('bad_frame',[
    pd.DataFrame(),frame('2023-12-05'),frame().iloc[-10:],
    frame().assign(Close=np.nan),frame().assign(Close=-1),frame().iloc[:-1],
])
def test_empty_stale_or_invalid_provider_data_never_becomes_live(market,monkeypatch,bad_frame):
    monkeypatch.setattr(market,'_download',lambda _:bad_frame)
    with pytest.raises(MarketDataUnavailable):market.history()


@pytest.fixture
def client(monkeypatch,market):
    from app import app
    import mvc.controllers.timeseries_controller as controller
    monkeypatch.setattr(controller,'market_data',market)
    monkeypatch.setitem(app.config,'TESTING',True)
    return app.test_client()


def test_default_page_and_api_use_recent_market_data(client,monkeypatch):
    import mvc.controllers.timeseries_controller as controller
    monkeypatch.setattr(controller.ts_model,'get_historical_data',lambda **_:pytest.fail('Live must not read CSV'))
    page=client.get('/timeseries')
    assert page.status_code==200 and b'2026-10-30' in page.data
    assert b'2023-12-05' not in page.data
    for source in (None,'live','dataset'):
        body={'steps':7}
        if source:body['source']=source
        response=client.post('/api/timeseries/forecast',json=body)
        assert response.status_code==200
        data=response.get_json()
        assert data['hist']['last_date']=='2026-10-30'
        assert data['forecast']['forecast_dates'][0]=='2026-11-02'
        assert data['meta']['source']=='live'


def test_csv_is_only_used_when_explicitly_requested(client,market,monkeypatch):
    monkeypatch.setattr(market,'history',lambda **_:pytest.fail('CSV must not query the network'))
    response=client.post('/api/timeseries/forecast',json={'source':'amzn_csv'})
    assert response.status_code==200
    data=response.get_json()
    assert data['hist']['last_date']=='2023-12-05'
    assert data['hist']['source']=='amzn_csv' and not data['hist']['is_live']
    assert 'Yahoo' not in data['hist']['source_label']
    page=client.get('/timeseries?source=amzn_csv')
    assert page.status_code==200 and b'id="dataSourceDot" hidden' in page.data


def test_provider_failure_keeps_csv_opt_in_and_returns_error(client,market,monkeypatch):
    def failure(_):raise TimeoutError('provider offline')
    monkeypatch.setattr(market,'_download',failure)
    response=client.get('/timeseries')
    assert response.status_code==503 and b'source=amzn_csv' in response.data
    assert b'2023-12-05' not in response.data
    response=client.post('/api/timeseries/forecast',json={'source':'live'})
    assert response.status_code==503 and not response.get_json()['success']
    assert 'hist' not in response.get_json()


@pytest.mark.parametrize('body',[
    {'source':'unknown'},{'source':'live','symbol':'AEP'},{'source':'amzn_csv','symbol':'AEP'},
    {'source':'aep_csv','symbol':'AMZN'},{'steps':0},{'steps':31},{'steps':1.5},{'steps':True},
    {'steps':'nan'},{'symbol':None},['invalid'],
])
def test_invalid_source_or_inputs_return_json_400(client,body):
    response=client.post('/api/timeseries/forecast',json=body)
    assert response.status_code==400 and not response.get_json()['success']


@pytest.mark.parametrize('last,expected',[
    ('2026-10-30',['2026-11-02','2026-11-03']),
    ('2026-11-25',['2026-11-27','2026-11-30']),
    ('2026-12-24',['2026-12-28','2026-12-29']),
])
def test_forecast_dates_skip_exchange_holidays(last,expected):
    from mvc.controllers.timeseries_controller import ts_model
    assert ts_model._generate_future_dates(last,2)==expected
