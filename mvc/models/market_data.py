"""Latest completed daily market sessions, separate from archived CSV datasets."""
import copy
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from mvc.models.model_errors import ModelUnavailableError

LOGGER = logging.getLogger(__name__)


class MarketDataUnavailable(ModelUnavailableError):
    pass


class MarketData:
    def __init__(self, workspace_dir):
        self.cache_dir=Path(workspace_dir)/'instance'/'market-cache'
        self._cache={}
        self._lock=threading.RLock()

    def _now(self):
        return datetime.now(timezone.utc)

    def _download(self,symbol):
        import yfinance as yf
        yf.set_tz_cache_location(str(self.cache_dir))
        return yf.Ticker(symbol).history(period='6mo',interval='1d',auto_adjust=False,timeout=10)

    def history(self,symbol='AMZN',limit=60):
        if symbol!='AMZN':
            raise ValueError('Nguồn thị trường hiện hỗ trợ AMZN. AEP_hourly là dữ liệu phụ tải điện ngoại tuyến.')
        with self._lock:
            try:
                now=pd.Timestamp(self._now())
                calendar=xcals.get_calendar('XNYS')
                sessions=calendar.sessions_in_range((now-timedelta(days=14)).date(),now.date())
                completed=[s for s in sessions if calendar.session_close(s)<=now]
                expected=completed[-1].strftime('%Y-%m-%d')
                cache_key=(symbol,limit)
                cached=self._cache.get(cache_key)
                if cached and time.monotonic()-cached[0]<300 and cached[1]['last_date']==expected:
                    return copy.deepcopy(cached[1])
                frame=self._download(symbol)
                if frame is None or frame.empty or 'Close' not in frame:
                    raise ValueError('Empty market response')
                close=pd.to_numeric(frame['Close'],errors='coerce')
                index=pd.DatetimeIndex(close.index)
                if index.tz is not None:
                    index=index.tz_convert('America/New_York')
                close=pd.Series(close.to_numpy(),index=index.strftime('%Y-%m-%d'))
                close=close[~close.index.duplicated(keep='last')].sort_index()
                close=close[np.isfinite(close.to_numpy()) & (close.to_numpy()>0)]
                close=close[[day<=expected and calendar.is_session(day) for day in close.index]].tail(limit)
                if len(close)<30 or close.index[-1]!=expected:
                    raise ValueError('Provider has not returned the latest completed session')
                result=dict(dates=close.index.tolist(),prices=[round(float(v),2) for v in close],
                    unit='USD',symbol=symbol,company_name='AMZN - Amazon.com Inc. (Mỹ)',
                    last_date=close.index[-1],last_price=round(float(close.iloc[-1]),2),
                    source='live',source_label='Yahoo Finance · Giá đóng cửa mới nhất',
                    source_url='https://finance.yahoo.com/quote/AMZN/history/',is_live=True,
                    fetched_at=now.isoformat(),timezone='America/New_York',data_kind='daily_close')
                self._cache[cache_key]=(time.monotonic(),copy.deepcopy(result))
                return result
            except Exception as error:
                LOGGER.warning('Latest market data unavailable: %s',type(error).__name__)
                raise MarketDataUnavailable('Chưa tải được phiên đóng cửa mới nhất từ Yahoo Finance. '
                    'Hãy thử lại hoặc chọn tệp CSV để xem dữ liệu lịch sử; hệ thống không thay bằng dữ liệu cũ.') from error
