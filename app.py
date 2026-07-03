import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import pandas_datareader.data as web
import requests
import FinanceDataReader as fdr

# 페이지 기본 설정
st.set_page_config(page_title="프라이빗 통합 투자 플랫폼", layout="wide")

# ==========================================
# 🔐 비밀번호 인증 기능
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "7777":  # 여기에 원하시는 비밀번호를 입력하세요
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("비밀번호가 틀렸습니다.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 🌟 공통 글로벌 변수 최상단 배치
# ==========================================
strat1_off = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ"]
strat1_def = ["IEF", "BIL"]
strat2_off = ["IBB", "IGV", "SKYY", "SOXX", "XLE", "XRT", "IEF", "DBC"]
strat2_def = ["IEF", "BIL"]
laa_assets = ["IWD", "GLD", "IEF", "QQQ", "SHY", "SPY"]
strat4_off = ["251350.KS", "133690.KS"]
strat4_def = ["153130.KS", "130680.KS", "308620.KS", "132030.KS"]

asset_names = {
    "251350.KS": "KODEX 선진국MSCI World", "133690.KS": "TIGER 미국나스닥100",
    "153130.KS": "KODEX 단기채권", "130680.KS": "TIGER 단기통안채",
    "308620.KS": "KODEX 미국채10년선물", "132030.KS": "KODEX 단기채권PLUS",
    "QQQ": "Invesco QQQ", "SPY": "SPDR S&P 500", "IEF": "iShares 7-10Y Treasury",
    "BIL": "SPDR 1-3M T-Bill", "SHY": "iShares 1-3Y Treasury", "GLD": "SPDR Gold",
    "IWD": "iShares Russell 1000 Value"
}

all_tickers = list(set(["TIP"] + strat1_off + strat1_def + strat2_off + strat2_def + laa_assets + strat4_off + strat4_def))

# ==========================================
# 🛡️ 야후 파이낸스 Rate Limit 차단 방지용 세션 위장
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 🧭 금액 콤마 처리용 안전 변환 함수 & 콜백 (달러 소수점 지원)
# ==========================================
def safe_float(val):
    if isinstance(val, str):
        val = val.replace(",", "").strip()
    try: return float(val)
    except: return 0.0

def format_number_str(key):
    val = str(st.session_state[key]).replace(",", "").strip()
    try:
        if val == "": st.session_state[key] = "0"
        else:
            f_val = float(val)
            if f_val.is_integer(): st.session_state[key] = f"{int(f_val):,}"
            else: st.session_state[key] = f"{f_val:,.2f}"
    except ValueError:
        st.session_state[key] = "0"

if "budget_stock" not in st.session_state: st.session_state.budget_stock = "15,000,000"
if "budget_idx" not in st.session_state: st.session_state.budget_idx = "15,000,000"
if "budget_asset" not in st.session_state: st.session_state.budget_asset = "100,000,000"
if "budget_dash1" not in st.session_state: st.session_state.budget_dash1 = "100,000,000"
if "budget_dash2" not in st.session_state: st.session_state.budget_dash2 = "100,000,000"
if "budget_dash3" not in st.session_state: st.session_state.budget_dash3 = "100,000,000"
if "budget_dash4" not in st.session_state: st.session_state.budget_dash4 = "100,000,000"

if "ui_pbr" not in st.session_state: st.session_state.ui_pbr = 1.20
if "ui_roe" not in st.session_state: st.session_state.ui_roe = 15.0
if "ui_price" not in st.session_state: st.session_state.ui_price = 10000.0
if "roe_val_3" not in st.session_state: st.session_state.roe_val_3 = 15.0
if "roe_val_5" not in st.session_state: st.session_state.roe_val_5 = 15.0
if "roe_val_10" not in st.session_state: st.session_state.roe_val_10 = 15.0

# ==========================================
# 🧭 DART 재무제표 파일 파싱 함수
# ==========================================
def parse_dart_files(files, comp_name):
    eq = [0.0, 0.0, 0.0]
    ni = [0.0, 0.0, 0.0]
    def to_float(val):
        try:
            v = str(val).replace(',', '').strip()
            if v == '-' or v == '': return 0.0
            return float(v)
        except: return 0.0
    for f in files:
        f.seek(0)
        try: df = pd.read_csv(f, sep='\t', encoding='utf-8')
        except:
            f.seek(0)
            try: df = pd.read_csv(f, sep='\t', encoding='cp949')
            except: continue
        if '회사명' not in df.columns or '항목명' not in df.columns: continue
        cdf = df[df['회사명'].astype(str).str.contains(comp_name, na=False)]
        if cdf.empty: continue
        eq_rows = cdf[cdf['항목명'].astype(str).str.contains('자본총계', na=False)]
        if not eq_rows.empty:
            for i, col in enumerate(['당기', '전기', '전전기']):
                if col in eq_rows.columns: eq[i] = to_float(eq_rows.iloc[0][col])
        ni_rows = cdf[cdf['항목명'].astype(str).str.contains('당기순이익', na=False)]
        if not ni_rows.empty:
            for i, col in enumerate(['당기', '전기', '전전기']):
                if col in ni_rows.columns: ni[i] = to_float(ni_rows.iloc[0][col])
    return eq, ni

# ==========================================
# 🧭 공통 기능: 데이터 로더 및 통화 감지
# ==========================================
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        t = yf.Ticker("KRW=X")
        price = float(t.history(period="1d")['Close'].iloc[-1])
        return price if price > 500 else 1350.0
    except: return 1350.0

def detect_currency(ticker):
    if not ticker or "직접 입력" in ticker: return "KRW"
    if ticker.endswith('.KS') or ticker.endswith('.KQ'): return "KRW"
    if ticker.isalpha(): return "USD"
    return "KRW"

@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://edition.cnn.com/markets/fear-and-greed',
            'Origin': 'https://edition.cnn.com'
        }
        res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return int(data['fear_and_greed']['score']), data['fear_and_greed']['rating'].title()
    except Exception as e: pass
    return None, None

@st.cache_data(ttl=86400)
def get_all_search_options():
    all_auto = []
    
    # 🛡️ 독립형 데이터 파싱 구조 기법 적용 (한 시장이 막혀도 나머지는 정상 작동)
    try:
        kospi = fdr.StockListing('KOSPI')
        all_auto.extend((kospi['Name'] + " (" + kospi['Code'] + ".KS)").tolist())
    except: pass
    
    try:
        kosdaq = fdr.StockListing('KOSDAQ')
        all_auto.extend((kosdaq['Name'] + " (" + kosdaq['Code'] + ".KQ)").tolist())
    except: pass
    
    try:
        etf = fdr.StockListing('ETF/KR')
        sym_col = 'Symbol' if 'Symbol' in etf.columns else 'Code'
        all_auto.extend((etf['Name'] + " (" + etf[sym_col] + ".KS)").tolist())
    except: pass
    
    try:
        sp500 = fdr.StockListing('S&P500')
        all_auto.extend((sp500['Name'] + " (" + sp500['Symbol'] + ")").tolist())
    except: pass
    
    try:
        nasdaq = fdr.StockListing('NASDAQ')
        all_auto.extend((nasdaq['Name'] + " (" + nasdaq['Symbol'] + ")").tolist())
    except: pass
    
    try:
        nyse = fdr.StockListing('NYSE')
        all_auto.extend((nyse['Name'] + " (" + nyse['Symbol'] + ")").tolist())
    except: pass
        
    # 만약 유저 통신 환경 문제 등으로 원본 API가 아예 다운됐을 때를 대비한 초강력 에센셜 백업 엔진
    essential_fallback = [
        "삼성전자 (005930.KS)", "SK하이닉스 (000660.KS)", "카카오 (035720.KS)", "NAVER (035420.KS)",
        "현대차 (005380.KS)", "LG에너지솔루션 (373220.KS)", "삼성바이오로직스 (207940.KS)",
        "KODEX 200 (069500.KS)", "TIGER 200 (102110.KS)", "KODEX 레버리지 (122630.KS)", "KODEX 200선물인버스2X (252670.KS)",
        "TIGER 미국나스닥100 (133690.KS)", "TIGER 미국S&P500 (360750.KS)", "KODEX 선진국MSCI World (251350.KS)",
        "KODEX 단기채권 (153130.KS)", "TIGER 단기통안채 (130680.KS)", "ACE KRX금현물 (411060.KS)"
    ]
    
    us_etfs_and_commodities = [
        "SPDR S&P 500 ETF (SPY)", "Invesco QQQ Trust (QQQ)", "Vanguard S&P 500 ETF (VOO)", "Invesco NASDAQ 100 ETF (QQQM)",
        "Vanguard Total Stock Market (VTI)", "iShares 20+ Year Treasury Bond (TLT)", "iShares 7-10 Year Treasury Bond (IEF)", 
        "iShares 1-3 Year Treasury Bond (SHY)", "SPDR Bloomberg 1-3 Month T-Bill (BIL)", 
        "ProShares Ultra QQQ (QLD)", "ProShares UltraPro QQQ (TQQQ)", "ProShares UltraPro Short QQQ (SQQQ)",
        "Direxion Daily Semiconductor Bull 3X (SOXL)", "Direxion Daily Semiconductor Bear 3X (SOXS)",
        "SPDR Gold Shares (GLD)", "Invesco DB Commodity Tracking (DBC)", "United States Oil Fund (USO)", 
        "Technology Select Sector SPDR (XLK)", "Health Care Select Sector SPDR (XLV)", "Financial Select Sector SPDR (XLF)", 
        "iShares Semiconductor ETF (SOXX)", "VanEck Semiconductor ETF (SMH)", "Schwab US Dividend Equity ETF (SCHD)",
        "Apple Inc. (AAPL)", "Microsoft Corp (MSFT)", "NVIDIA Corp (NVDA)", "Amazon.com Inc (AMZN)", "Tesla Inc (TSLA)"
    ]
    
    combined = list(set(all_auto + essential_fallback + us_etfs_and_commodities))
    return ["직접 입력 (여기에 없는 종목)"] + sorted(combined)

@st.cache_data(ttl=600)
def get_stock_info(ticker):
    if not ticker or ticker == "직접 입력": return 0.0, 0.0
    price, dividend = 0.0, 0.0
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        code = ticker.split('.')[0]
        try:
            res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/basic", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if res.status_code == 200: price = float(res.json()['result']['closePrice'].replace(',', ''))
        except: pass
    try:
        t = yf.Ticker(ticker)
        if price == 0.0:
            hist = t.history(period="1d")
            if not hist.empty: price = float(hist['Close'].iloc[-1])
        info = t.info
        div = info.get('dividendRate')
        if div is None: div = info.get('trailingAnnualDividendRate', 0.0)
        dividend = float(div) if div is not None else 0.0
    except: pass
    return price, dividend

@st.cache_data(ttl=3600)
def get_pbr_roe_price(ticker):
    if not ticker or "직접 입력" in ticker: return 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        price = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
        
        pbr = 0.0
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            code = ticker.split('.')[0]
            try:
                res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/basic", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                if res.status_code == 200: pbr = float(res.json()['result']['pbr'])
            except: pass
            
        if pbr == 0.0:
            info = t.info
            bps = info.get('bookValue', 0)
            if bps and bps > 0 and price > 0: pbr = price / bps
            else: pbr = info.get('priceToBook', 1.0)
        if not pbr or pbr <= 0: pbr = 1.0
        
        roes = []
        try:
            inc = t.financials
            bs = t.balance_sheet
            ni_keys = ['Net Income', 'NetIncome', 'Net Income Common Stockholders']
            eq_keys = ['Stockholders Equity', 'Total Stockholder Equity']
            ni_row, eq_row = None, None
            for k in ni_keys:
                if k in inc.index: ni_row = inc.loc[k]; break
            for k in eq_keys:
                if k in bs.index: eq_row = bs.loc[k]; break
            if ni_row is not None and eq_row is not None:
                for date in ni_row.index:
                    if date in eq_row.index:
                        ni_val, eq_val = ni_row[date], eq_row[date]
                        if pd.notna(ni_val) and pd.notna(eq_val) and eq_val > 0:
                            roes.append((ni_val / eq_val) * 100)
        except: pass
        
        current_roe = t.info.get('returnOnEquity', 0.0) * 100 if t.info.get('returnOnEquity') else 0.0
        avg_roe_3 = sum(roes[:3]) / len(roes[:3]) if len(roes[:3]) > 0 else current_roe
        avg_roe_5 = sum(roes[:5]) / len(roes[:5]) if len(roes[:5]) > 0 else avg_roe_3
        avg_roe_10 = sum(roes[:10]) / len(roes[:10]) if len(roes[:10]) > 0 else avg_roe_5
        
        return float(pbr), float(avg_roe_3), float(avg_roe_5), float(avg_roe_10), float(price)
    except: return 1.0, 0.0, 0.0, 0.0, 0.0

@st.cache_data(ttl=14400)
def load_financial_data(tickers):
    start_date = "2010-01-01" 
    df = yf.download(tickers, start=start_date, threads=False, session=yf_session)
    if 'Close' in df.columns: df = df['Close']
    return df.ffill().dropna(how='all')

@st.cache_data(ttl=14400)
def load_fred_data():
    start_date = "2010-01-01"
    return web.DataReader("UNRATE", "fred", start_date)

def get_baa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6, 9, 12]])

def get_aaa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6]])

# ==========================================
# 📊 대시보드 내부 백테스팅 엔진 (거치식/적립식 통합 모델)
# ==========================================
@st.cache_data(ttl=86400)
def get_dashboard_backtest(strat_id, m_data, d_data, unrate_data, inv_type="거치식"):
    try:
        port_rets, idx_dates = [], []
        if strat_id == 1 or strat_id == 2:
            off_tkrs = strat1_off if strat_id == 1 else strat2_off
            def_tkrs = strat1_def if strat_id == 1 else strat2_def
            
            off_tkrs = [t for t in off_tkrs if t in m_data.columns]
            def_tkrs = [t for t in def_tkrs if t in m_data.columns]
            tickers = list(set(["TIP"] + off_tkrs + def_tkrs))
            tickers = [t for t in tickers if t in m_data.columns]
            
            df = m_data[tickers].dropna()
            if len(df) < 13 or "TIP" not in df.columns: return None, None
            
            mom_1 = df / df.shift(1) - 1; mom_3 = df / df.shift(3) - 1
            mom_6 = df / df.shift(6) - 1; mom_9 = df / df.shift(9) - 1; mom_12 = df / df.shift(12) - 1
            baa_scores = mom_1 + mom_3 + mom_6 + mom_9 + mom_12
            
            for i in range(12, len(df)-1):
                curr_date, next_date = df.index[i], df.index[i+1]
                tip_score = baa_scores.loc[curr_date, "TIP"]
                if tip_score > 0 and off_tkrs:
                    top4 = baa_scores.loc[curr_date, off_tkrs].nlargest(4).index
                    weights = {t: 0.25 for t in top4}
                elif def_tkrs:
                    top1 = baa_scores.loc[curr_date, def_tkrs].nlargest(1).index
                    weights = {t: 1.0 for t in top1}
                else: continue
                    
                ret = sum([weights[t] * (df.loc[next_date, t] / df.loc[curr_date, t] - 1) for t in weights])
                port_rets.append(float(ret)); idx_dates.append(next_date)
                
        elif strat_id == 3:
            valid_laa = [t for t in laa_assets if t in m_data.columns]
            df = m_data[valid_laa].dropna()
            if len(df) < 13 or "SPY" not in d_data.columns or "UNRATE" not in unrate_data.columns: return None, None
            
            d_spy = d_data['SPY'].dropna(); d_spy_200 = d_spy.rolling(200).mean()
            u_df = unrate_data['UNRATE'].dropna(); u_12 = u_df.rolling(12).mean()
            
            for i in range(12, len(df)-1):
                curr_date, next_date = df.index[i], df.index[i+1]
                spy_mask = d_spy.index <= curr_date
                if not spy_mask.any(): continue
                spy_prev, spy_200_prev = d_spy[spy_mask].iloc[-1], d_spy_200[spy_mask].iloc[-1]
                ur_mask = u_df.index <= curr_date
                if not ur_mask.any(): continue
                ur_prev, ur_12_prev = u_df[ur_mask].iloc[-1], u_12[ur_mask].iloc[-1]
                
                weights = {}
                for t in ["IWD", "GLD", "IEF"]: 
                    if t in df.columns: weights[t] = 0.25
                
                if spy_prev < spy_200_prev and ur_prev > ur_12_prev: 
                    if "SHY" in df.columns: weights["SHY"] = 0.25
                else: 
                    if "QQQ" in df.columns: weights["QQQ"] = 0.25
                    
                if weights:
                    ret = sum([weights[t] * (df.loc[next_date, t] / df.loc[curr_date, t] - 1) for t in weights])
                    port_rets.append(float(ret)); idx_dates.append(next_date)
                
        elif strat_id == 4:
            off_tkrs = [t for t in strat4_off if t in m_data.columns]
            def_tkrs = [t for t in strat4_def if t in m_data.columns]
            tickers = list(set(off_tkrs + def_tkrs))
            df = m_data[tickers].dropna()
            if len(df) < 7: return None, None
            
            mom_1 = df / df.shift(1) - 1; mom_3 = df / df.shift(3) - 1; mom_6 = df / df.shift(6) - 1
            aaa_scores = mom_1 + mom_3 + mom_6
            
            for i in range(6, len(df)-1):
                curr_date, next_date = df.index[i], df.index[i+1]
                max_sc = aaa_scores.loc[curr_date, off_tkrs].max() if off_tkrs else -999
                
                if max_sc > 0 and off_tkrs:
                    top1 = aaa_scores.loc[curr_date, off_tkrs].nlargest(1).index
                    weights = {t: 1.0 for t in top1}
                elif def_tkrs:
                    top1 = mom_1.loc[curr_date, def_tkrs].nlargest(1).index
                    weights = {t: 1.0 for t in top1}
                else: continue
                    
                ret = sum([weights[t] * (df.loc[next_date, t] / df.loc[curr_date, t] - 1) for t in weights])
                port_rets.append(float(ret)); idx_dates.append(next_date)
                
        if not port_rets: return None, None
        
        if 'SPY' not in m_data.columns: return None, None
        spy_m = m_data['SPY'].dropna()
        if 'QQQ' in m_data.columns: qqq_m = m_data['QQQ'].dropna()
        else: qqq_m = load_financial_data(['QQQ']).resample('ME').last()
        
        port_series = pd.Series(port_rets, index=idx_dates)
        s_rets_full = spy_m.pct_change().dropna()
        q_rets_full = qqq_m.pct_change().dropna()
        
        common_dates = port_series.index.intersection(s_rets_full.index).intersection(q_rets_full.index)
        if len(common_dates) < 2: return None, None
        
        p_rets = port_series.loc[common_dates]
        s_rets = s_rets_full.loc[common_dates]
        q_rets = q_rets_full.loc[common_dates]
        
        years = len(common_dates) / 12
        
        if inv_type == "월적립식":
            p_bal, s_bal, q_bal, pr_list = [], [], [], []
            p_curr, s_curr, q_curr, pr = 0, 0, 0, 0
            
            for d in common_dates:
                pr += 100
                pr_list.append(pr)
                p_curr = (p_curr + 100) * (1 + p_rets[d])
                s_curr = (s_curr + 100) * (1 + s_rets[d])
                q_curr = (q_curr + 100) * (1 + q_rets[d])
                
                p_bal.append(p_curr)
                s_bal.append(s_curr)
                q_bal.append(q_curr)
                
            p_bal = pd.Series(p_bal, index=common_dates)
            s_bal = pd.Series(s_bal, index=common_dates)
            q_bal = pd.Series(q_bal, index=common_dates)
            pr_series = pd.Series(pr_list, index=common_dates)
            
            p_tot = (p_bal.iloc[-1] / pr_series.iloc[-1]) - 1
            s_tot = (s_bal.iloc[-1] / pr_series.iloc[-1]) - 1
            q_tot = (q_bal.iloc[-1] / pr_series.iloc[-1]) - 1
            
            p_cagr = ((p_tot + 1) ** (2 / years)) - 1 if years > 0 else 0
            s_cagr = ((s_tot + 1) ** (2 / years)) - 1 if years > 0 else 0
            q_cagr = ((q_tot + 1) ** (2 / years)) - 1 if years > 0 else 0
            
            p_mdd = (p_bal / p_bal.cummax() - 1).min()
            s_mdd = (s_bal / s_bal.cummax() - 1).min()
            q_mdd = (q_bal / q_bal.cummax() - 1).min()
            
            chart_df = pd.DataFrame({
                "전략 포트폴리오 (적립식)": (p_bal / pr_series) * 100,
                "SPY (적립식)": (s_bal / pr_series) * 100,
                "QQQ (적립식)": (q_bal / pr_series) * 100,
                "투자 원금 (Break-even)": 100.0
            })
            
        else: 
            p_cum = (1 + p_rets).cumprod() * 100
            s_cum = (1 + s_rets).cumprod() * 100
            q_cum = (1 + q_rets).cumprod() * 100
            
            p_tot = (p_cum.iloc[-1] / 100) - 1
            s_tot = (s_cum.iloc[-1] / 100) - 1
            q_tot = (q_cum.iloc[-1] / 100) - 1
            
            p_cagr = ((p_tot + 1) ** (1 / years)) - 1 if years > 0 else 0
            s_cagr = ((s_tot + 1) ** (1 / years)) - 1 if years > 0 else 0
            q_cagr = ((q_tot + 1) ** (1 / years)) - 1 if years > 0 else 0
            
            p_mdd = (p_cum / p_cum.cummax() - 1).min()
            s_mdd = (s_cum / s_cum.cummax() - 1).min()
            q_mdd = (q_cum / q_cum.cummax() - 1).min()
            
            chart_df = pd.DataFrame({
                "전략 포트폴리오 (거치식)": p_cum, 
                "SPY (거치식)": s_cum,
                "QQQ (거치식)": q_cum
            })
            
        p_sharpe = (p_rets.mean() / p_rets.std() * np.sqrt(12)) if p_rets.std() != 0 else 0
        s_sharpe = (s_rets.mean() / s_rets.std() * np.sqrt(12)) if s_rets.std() != 0 else 0
        q_sharpe = (q_rets.mean() / q_rets.std() * np.sqrt(12)) if q_rets.std() != 0 else 0
        
        metrics = {
            "p_tot": p_tot, "s_tot": s_tot, "q_tot": q_tot,
            "p_cagr": p_cagr, "s_cagr": s_cagr, "q_cagr": q_cagr,
            "p_mdd": p_mdd, "s_mdd": s_mdd, "q_mdd": q_mdd,
            "p_sharpe": p_sharpe, "s_sharpe": s_sharpe, "q_sharpe": q_sharpe
        }
        return metrics, chart_df
    except Exception as e:
        return None, None

def render_dashboard_backtest_ui(strat_id, m_data, d_data, unrate_data):
    st.write(f"#### 📊 전략 누적 성과 백테스트 ({strat_id}번 전략)")
    
    inv_type = st.radio(
        "💡 백테스트 투자 방식 선택", 
        ["거치식", "월적립식"], 
        horizontal=True, 
        key=f"inv_type_dash_{strat_id}"
    )
    
    metrics, chart_df = get_dashboard_backtest(strat_id, m_data, d_data, unrate_data, inv_type)
    
    if chart_df is not None:
        col_m, col_c = st.columns([1, 2])
        with col_m:
            start_dt = chart_df.index[0].strftime('%Y-%m-%d')
            end_dt = chart_df.index[-1].strftime('%Y-%m-%d')
            st.markdown(f"**🗓️ 데이터 반영 기간:** `{start_dt}` ~ `{end_dt}`")
            if inv_type == "월적립식":
                st.caption("ℹ️ *월적립식 CAGR은 누적된 투자원금의 평균 거치기간을 고려한 근사치(Modified)로 표현됩니다.*")
            
            html_table = f"""
            <div style="background-color: #1e2130; padding: 16px; border-radius: 12px; border: 1px solid #2e3147; margin-bottom: 20px;">
                <table style="width:100%; text-align:right; font-size:1em; border-collapse: collapse;">
                    <tr style="border-bottom: 2px solid #4f8ef7; color:#8b90a8;">
                        <th style="text-align:left; padding:8px;">{inv_type} 성과</th>
                        <th style="padding:8px; color:#4f8ef7;">포트폴리오</th>
                        <th style="padding:8px;">SPY</th>
                        <th style="padding:8px;">QQQ</th>
                    </tr>
                    <tr style="border-bottom: 1px solid #2e3147;">
                        <td style="text-align:left; padding:10px; font-weight:bold; color:#e8eaf0;">총 수익률</td>
                        <td style="padding:10px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{metrics['p_tot']*100:,.2f}%</td>
                        <td style="padding:10px; color:#e8eaf0;">{metrics['s_tot']*100:,.2f}%</td>
                        <td style="padding:10px; color:#e8eaf0;">{metrics['q_tot']*100:,.2f}%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #2e3147;">
                        <td style="text-align:left; padding:10px; font-weight:bold; color:#e8eaf0;">CAGR</td>
                        <td style="padding:10px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{metrics['p_cagr']*100:,.2f}%</td>
                        <td style="padding:10px; color:#e8eaf0;">{metrics['s_cagr']*100:,.2f}%</td>
                        <td style="padding:10px; color:#e8eaf0;">{metrics['q_cagr']*100:,.2f}%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #2e3147;">
                        <td style="text-align:left; padding:10px; font-weight:bold; color:#e74c3c; font-weight:bold; font-size:1.1em;">{metrics['p_mdd']*100:,.2f}%</td>
                        <td style="padding:10px; color:#8b90a8;">{metrics['s_mdd']*100:,.2f}%</td>
                        <td style="padding:10px; color:#8b90a8;">{metrics['q_mdd']*100:,.2f}%</td>
                    </tr>
                    <tr>
                        <td style="text-align:left; padding:10px; font-weight:bold; color:#e8eaf0;">Sharpe</td>
                        <td style="padding:10px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{metrics['p_sharpe']:.2f}</td>
                        <td style="padding:10px; color:#8b90a8;">{metrics['s_sharpe']:.2f}</td>
                        <td style="padding:10px; color:#8b90a8;">{metrics['q_sharpe']:.2f}</td>
                    </tr>
                </table>
            </div>
            """
            st.markdown(html_table, unsafe_allow_html=True)
            
        with col_c:
            chart_title = "누적 자산 추이 (초기 투자 100 기준)" if inv_type == "거치식" else "원금 대비 자산 평가 비율 (원금=100 본전선)"
            st.write(f"📈 **{chart_title}**")
            st.line_chart(chart_df)
    else:
        st.info("데이터가 부족하여 백테스트를 수행할 수 없습니다.")

def render_dashboard_rebalancer(strat_id, buy_dict, data_df):
    st.write("#### 🧮 전략 맞춤형 실시간 리밸런싱 계산기")
    b_col1, b_col2 = st.columns([1, 3])
    budget_key = f"budget_dash{strat_id}"
    budget_str = b_col1.text_input("총 투자 운용 금액 (원)", key=budget_key, on_change=format_number_str, args=(budget_key,))
    budget = safe_float(budget_str)
    
    df_list = []
    for tkr, w in buy_dict.items():
        price = 0.0
        if tkr in data_df.columns: price = float(data_df[tkr].iloc[-1])
        if price == 0.0 or pd.isna(price): price, _ = get_stock_info(tkr)
            
        weight = float(w.replace('%', '')) if isinstance(w, str) else float(w)
        df_list.append({
            "Ticker": tkr,
            "자산명": asset_names.get(tkr, tkr),
            "목표비중(%)": weight,
            "현재가(원)": int(price),
            "보유수량(주)": 0
        })
        
    if df_list:
        base_df = pd.DataFrame(df_list)
        st.caption("💡 **안내:** 현재 계좌에 보유 중인 수량을 **[보유수량(주)]** 칸에 직접 입력하셔야 정확한 '살 종목수(추가매수/매도)'가 연산됩니다.")
        edited_df = st.data_editor(base_df, disabled=["Ticker", "자산명", "목표비중(%)"], use_container_width=True, key=f"dash_edit_{strat_id}")
        res_df = edited_df.copy()
        res_df["목표수량(주)"] = np.floor((budget * (res_df["목표비중(%)"]/100)) / res_df["현재가(원)"]).replace([np.inf, -np.inf, np.nan], 0)
        res_df["살 종목수(주)"] = res_df["목표수량(주)"] - res_df["보유수량(주)"]
        
        def color_action(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}; font-weight: bold;'
            
        styled_df = res_df.style.format({"현재가(원)": "{:,.0f}원", "보유수량(주)": "{:,.0f}주", "목표수량(주)": "{:,.0f}주", "살 종목수(주)": "{:,.0f}주"})
        if hasattr(styled_df, "map"): styled_df = styled_df.map(color_action, subset=["살 종목수(주)"])
        else: styled_df = styled_df.applymap(color_action, subset=["살 종목수(주)"])
        st.dataframe(styled_df, use_container_width=True)

def get_fmt(val, curr):
    if val == 0: return ""
    return f"{int(val):,}" if curr == "KRW" else f"{val:.2f}"

# ==========================================
# 🎨 메인 타이틀 및 F&G 배너
# ==========================================
st.markdown("<h1 style='text-align: center;'>📊 프라이빗 투자 플랫폼</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b90a8; margin-top: -10px; margin-bottom: 30px;'>물타기 · 지수분할 · 가치평가 모델링 · 자산배분 및 백테스트 통합 엔진</p>", unsafe_allow_html=True)

fng_score, fng_rating = get_fear_and_greed()

if fng_score is not None:
    color_map = {
        "Extreme Fear": ("#e74c3c", "rgba(231,76,60,0.15)"),
        "Fear": ("#e67e22", "rgba(230,126,34,0.15)"),
        "Neutral": ("#f1c40f", "rgba(241,196,15,0.15)"),
        "Greed": ("#2ecc71", "rgba(46,204,113,0.15)"),
        "Extreme Greed": ("#27ae60", "rgba(39,174,96,0.15)")
    }
    text_color, bg_color = color_map.get(fng_rating, ("#f1c40f", "rgba(241,196,15,0.1)"))
    score_html = f'<span style="font-size: 0.6em; padding: 4px 12px; border-radius: 20px; background: {bg_color}; color: {text_color}; border: 1px solid {text_color}; text-transform: uppercase; margin-right: 12px;">{fng_rating}</span> <span style="font-size: 1.4em;">{fng_score}</span>'
else:
    score_html = '<span style="font-size: 0.9em; font-weight: 500; color: #8b90a8;">지수 불러오는 중...</span>'

banner_html = f"""
<div style="background-color: #222536; border: 1px solid #2e3147; border-radius: 12px; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
    <div style="font-weight: 700; color: #e8eaf0; font-size: 1.1em; display: flex; align-items: center; gap: 8px;">
        🧭 CNN Fear & Greed Index
    </div>
    <div style="font-size: 1.6em; font-weight: 800; color: #e8eaf0; display: flex; align-items: center;">
        {score_html}
    </div>
</div>
"""
st.markdown(banner_html, unsafe_allow_html=True)

# ==========================================
# 🧭 사이드바 설정
# ==========================================
st.sidebar.title("네비게이션")
app_mode = st.sidebar.radio("원하시는 기능을 선택하세요:", ["🧮 프라이빗 투자 계산기", "📊 동적 자산배분 대시보드"])
st.sidebar.caption("데이터 제공: Yahoo Finance, FRED, Naver, DART, CNN")

# ==========================================
# 1. 🧮 프라이빗 투자 계산기
# ==========================================
if app_mode == "🧮 프라이빗 투자 계산기":
    
    with st.spinner("글로벌 종목 데이터를 동기화 중입니다..."):
        SEARCH_OPTIONS = get_all_search_options()
        EXCH_RATE = get_exchange_rate()
    
    tab_stock, tab_idx, tab_asset, tab_backtest, tab_roe = st.tabs([
        "📊 개별종목 물타기", "📉 지수 물타기", "🗂️ 자산배분 리밸런싱", "⏳ 자산배분 백테스트", "📈 기대수익률(R) 스마트"
    ])
    
    # --- 1. 개별종목 물타기 ---
    with tab_stock:
        st.write("개별종목 분할매수 스케줄 계산")
        st.info("💡 **안내:** 검색 후 종목의 현재가나 배당금이 보이지 않는다면 수동으로 입력해 주세요. (미국 종목은 자동으로 달러로 계산됩니다)")
        
        selected_stock = st.selectbox("🔍 종목 검색 (한국 및 미국 전 종목/원자재/레버리지 ETF 동시 검색)", options=SEARCH_OPTIONS, index=1)
        
        stock_ticker = ""
        if selected_stock == "직접 입력 (여기에 없는 종목)":
            stock_ticker = st.text_input("종목 코드 직접 입력 (예: 005930.KS, TQQQ)")
        else:
            stock_ticker = selected_stock.split("(")[-1].replace(")", "").strip()
            
        fetched_price, fetched_div = get_stock_info(stock_ticker) if stock_ticker else (0.0, 0.0)
        
        auto_curr = detect_currency(stock_ticker)
        curr_override = st.radio("통화 기준 선택", ["자동 인식", "원화 (KRW)", "달러 (USD)"], horizontal=True, key="curr_stock")
        final_curr = auto_curr if curr_override == "자동 인식" else ("KRW" if "KRW" in curr_override else "USD")
        sym = "원" if final_curr == "KRW" else "$"
        
        c1, c2, c3, c4 = st.columns(4)
        budget_str = c1.text_input(f"총 투자 금액 ({sym})", key="budget_stock", on_change=format_number_str, args=("budget_stock",))
        start_price_str = c2.text_input(f"1회차 매수 가격 ({sym})", value=get_fmt(fetched_price, final_curr) if fetched_price > 0 else "", placeholder="수동 입력", key=f"sp_{stock_ticker}")
        dividend_input_str = c3.text_input(f"예상 주당 배당금 ({sym})", value=get_fmt(fetched_div, final_curr) if fetched_div > 0 else "0", key=f"div_{stock_ticker}")
        steps = c4.number_input("분할 횟수", min_value=2, max_value=20, value=5)
        
        budget = safe_float(budget_str)
        start_price = safe_float(start_price_str)
        dividend_input = safe_float(dividend_input_str)
        
        st.divider()
        st.write("⚙️ **세부 분할매수 조건 설정**")
        
        # 1. 하락폭 설정
        drop_type = st.radio("하락폭 설정", ["일괄 (매회 동일)", "직접 입력"], horizontal=True)
        drops = []
        if drop_type == "일괄 (매회 동일)":
            fixed_drop_str = st.text_input(f"회당 하락 금액 ({sym})", value="1,000" if final_curr == "KRW" else "1.50")
            fixed_drop = safe_float(fixed_drop_str)
            drops = [fixed_drop] * (steps - 1)
        else:
            st.write(f"회차별 하락 금액 설정 ({sym}, 이전 회차 대비)")
            drop_cols = st.columns(steps - 1)
            for i in range(steps - 1):
                val_str = drop_cols[i].text_input(f"{i+1}➔{i+2}차", value="1,000" if final_curr == "KRW" else "1.50", key=f"drop_{i}")
                drops.append(safe_float(val_str))
                
        st.write("") # 여백
        
        # 2. 배수(비중) 설정
        mult_type = st.radio("회차별 매수 비중(배수) 설정", ["점진적 증가 (1, 2, 3... 배수)", "직접 입력 (마틴게일 등)"], horizontal=True)
        multipliers = []
        if mult_type == "점진적 증가 (1, 2, 3... 배수)":
            multipliers = [float(i) for i in range(1, steps + 1)]
        else:
            st.write("회차별 매수 배수 직접 입력 (예: 1차 1배수, 2차 2배수, 3차 4배수...)")
            mult_cols = st.columns(steps)
            for i in range(steps):
                m_val = mult_cols[i].number_input(f"{i+1}차 배수", min_value=0.1, value=float(i+1), step=1.0, key=f"mult_{i}")
                multipliers.append(m_val)
                
        if st.button("개별종목 계산하기", type="primary"):
            if start_price <= 0:
                st.error("❗ 매수 가격이 0이거나 입력되지 않았습니다. 현재가를 수동으로 입력해 주세요.")
            else:
                w_sum = sum(multipliers)
                res, t_spent, t_shares = [], 0, 0
                curr_price = start_price
                
                for i in range(1, steps + 1):
                    target_amt = budget * (multipliers[i-1] / w_sum)
                    if i > 1: curr_price -= drops[i-2]
                    if curr_price <= 0: break
                    
                    shares = int(target_amt / curr_price)
                    actual = shares * curr_price
                    t_spent += actual
                    t_shares += shares
                    res.append({
                        "회차": f"{i}차 ({multipliers[i-1]:g}배수)", 
                        "목표금액": target_amt, 
                        "매수가격": curr_price, 
                        "매수수량": shares, 
                        "체결금액": actual
                    })
                
                fmt_rule = "{:,.0f}원" if final_curr == "KRW" else "{:,.2f}$"
                st.dataframe(pd.DataFrame(res).style.format({"목표금액": fmt_rule, "매수가격": fmt_rule, "체결금액": fmt_rule, "매수수량": "{:,.0f}주"}), use_container_width=True)
                
                avg_price = (t_spent/t_shares) if t_shares > 0 else 0
                yield_rate = (dividend_input / avg_price) * 100 if avg_price > 0 and dividend_input > 0 else 0.0
                
                avg_disp = f"{int(avg_price):,}원" if final_curr == "KRW" else f"{avg_price:,.2f}$"
                spent_disp = f"{int(t_spent):,}원" if final_curr == "KRW" else f"{t_spent:,.2f}$"
                st.success(f"**총 매수금액:** {spent_disp} | **평균단가:** {avg_disp} | **예상 배당률:** {yield_rate:.2f}% | **누적수량:** {t_shares:,.0f}주")

    # --- 2. 지수 물타기 ---
    with tab_idx:
        st.write("지수/ETF 분할매수 스케줄 계산")
        st.info("💡 **안내:** 검색 후 종목의 현재가가 자동으로 나오지 않는다면 수동으로 입력해 주세요. (미국 ETF는 달러로 자동 변환됩니다)")
        
        default_idx = next((i for i, x in enumerate(SEARCH_OPTIONS) if "069500" in x), 1)
        selected_idx = st.selectbox("🔍 지수/원자재/ETF 검색", options=SEARCH_OPTIONS, index=default_idx, key="idx_search") 
        
        idx_ticker = ""
        if selected_idx == "직접 입력 (여기에 없는 종목)":
            idx_ticker = st.text_input("ETF 코드 직접 입력", key="idx_custom")
        else:
            idx_ticker = selected_idx.split("(")[-1].replace(")", "").strip()
            
        fetched_idx_price, _ = get_stock_info(idx_ticker) if idx_ticker else (0.0, 0.0)

        auto_curr_idx = detect_currency(idx_ticker)
        curr_override_idx = st.radio("통화 기준 선택", ["자동 인식", "원화 (KRW)", "달러 (USD)"], horizontal=True, key="curr_idx")
        final_curr_idx = auto_curr_idx if curr_override_idx == "자동 인식" else ("KRW" if "KRW" in curr_override_idx else "USD")
        sym_idx = "원" if final_curr_idx == "KRW" else "$"

        i1, i2, i3, i4 = st.columns(4)
        idx_budget_str = i1.text_input(f"지수 총 투자 금액 ({sym_idx})", key="budget_idx", on_change=format_number_str, args=("budget_idx",))
        idx_start_str = i2.text_input(f"첫 매수 지수/단가 ({sym_idx})", value=get_fmt(fetched_idx_price, final_curr_idx) if fetched_idx_price > 0 else "", placeholder="수동 입력", key=f"idx_p_{idx_ticker}")
        idx_drop = i3.number_input("구간별 하락률 (%)", value=5.0, step=0.5)
        idx_steps = i4.number_input("지수 분할 횟수", min_value=2, max_value=20, value=5)
        
        idx_budget = safe_float(idx_budget_str)
        idx_start = safe_float(idx_start_str)
        
        if st.button("지수 계산하기", type="primary"):
            if idx_start <= 0:
                st.error("❗ 첫 매수 지수/단가가 0원이거나 입력되지 않았습니다. 현재가를 수동으로 입력해 주세요.")
            else:
                w_sum = (idx_steps * (idx_steps + 1)) / 2
                res_idx, t_spent_idx, t_shares_idx = [], 0, 0
                
                for i in range(1, idx_steps + 1):
                    target_amt = idx_budget * (i / w_sum)
                    curr_idx = idx_start * (1 - (idx_drop / 100) * (i - 1))
                    if curr_idx <= 0: break
                    
                    shares = int(target_amt / curr_idx)
                    actual = shares * curr_idx
                    t_spent_idx += actual
                    t_shares_idx += shares
                    res_idx.append({"회차": f"{i}차 (-{idx_drop*(i-1)}%)", "목표금액": target_amt, "매수지수(단가)": curr_idx, "매수수량": shares, "체결금액": actual})
                
                fmt_rule_idx = "{:,.0f}원" if final_curr_idx == "KRW" else "{:,.2f}$"
                st.dataframe(pd.DataFrame(res_idx).style.format({"목표금액": fmt_rule_idx, "매수지수(단가)": fmt_rule_idx, "체결금액": fmt_rule_idx, "매수수량": "{:,.0f}주"}), use_container_width=True)
                
                avg_p_idx = (t_spent_idx/t_shares_idx) if t_shares_idx > 0 else 0
                avg_disp_idx = f"{int(avg_p_idx):,}원" if final_curr_idx == "KRW" else f"{avg_p_idx:,.2f}$"
                spent_disp_idx = f"{int(t_spent_idx):,}원" if final_curr_idx == "KRW" else f"{t_spent_idx:,.2f}$"
                st.success(f"**총 매수금액:** {spent_disp_idx} | **평균단가:** {avg_disp_idx} | **누적수량:** {t_shares_idx:,.0f}주")

    # --- 3. 자산배분 리밸런싱 ---
    with tab_asset:
        st.write("포트폴리오 비중 조절 (리밸런싱) 계산기")
        
        base_curr = st.radio("총 투자 운용 금액의 기준 통화 (결과 연산 기준)", ["원화 (KRW)", "달러 (USD)"], horizontal=True)
        base_sym = "원" if base_curr == "원화 (KRW)" else "$"
        st.caption(f"💱 **적용 중인 실시간 환율:** {EXCH_RATE:,.2f} 원/달러 (야후 파이낸스 기준)")
        
        total_asset_budget_str = st.text_input(f"총 투자 운용 금액 ({base_sym})", key="budget_asset", on_change=format_number_str, args=("budget_asset",))
        total_asset_budget = safe_float(total_asset_budget_str)
        
        if 'asset_df_base' not in st.session_state:
            st.session_state.asset_df_base = pd.DataFrame([
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "069500" in x), "직접 입력"), "티커 직접입력": "", "통화": "KRW", "현재가": 35000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "360750" in x), "직접 입력"), "티커 직접입력": "", "통화": "KRW", "현재가": 15000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "308620" in x), "직접 입력"), "티커 직접입력": "", "통화": "KRW", "현재가": 11000.0, "목표비중(%)": 20.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "411060" in x), "직접 입력"), "티커 직접입력": "", "통화": "KRW", "현재가": 13000.0, "목표비중(%)": 20.0, "보유수량(주)": 0}
            ])
            
        column_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 글로벌 전체 검색)", options=SEARCH_OPTIONS, width="large"),
            "티커 직접입력": st.column_config.TextColumn("티커 직접입력 (예: AAPL, 005930.KS)"),
            "통화": st.column_config.SelectboxColumn("통화", options=["KRW", "USD"]),
            "현재가": st.column_config.NumberColumn("현재가", format="%.2f"),
            "목표비중(%)": st.column_config.NumberColumn("목표비중(%)", min_value=0.0, max_value=100.0),
            "보유수량(주)": st.column_config.NumberColumn("보유수량(주)", min_value=0, format="%d")
        }

        st.caption("💡 **안내:** 목록에 없는 종목은 '자산명'을 [직접 입력]으로 두고 **'티커 직접입력'** 칸에 티커를 적어주세요. 미국/한국 자산이 섞여도 환율이 자동 적용되어 '살 종목수'가 계산됩니다.")
        edited_df = st.data_editor(st.session_state.asset_df_base, num_rows="dynamic", column_config=column_config, use_container_width=True, key="asset_editor")
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            if st.button("🔄 현재가 및 통화 일괄 업데이트"):
                with st.spinner("현재가 및 통화 설정을 실시간으로 조회중입니다..."):
                    updated_df = edited_df.copy()
                    for idx, row in updated_df.iterrows():
                        ticker = str(row.get("티커 직접입력", "")).strip()
                        if not ticker or ticker == "nan" or ticker == "None":
                            asset_str = row["자산명 (선택)"]
                            if asset_str and "(" in asset_str:
                                ticker = asset_str.split("(")[-1].replace(")", "").strip()
                        
                        if ticker:
                            price, _ = get_stock_info(ticker)
                            if price > 0:
                                updated_df.at[idx, "현재가"] = price
                                updated_df.at[idx, "통화"] = detect_currency(ticker)
                    st.session_state.asset_df_base = updated_df
                    st.rerun()

        total_ratio = edited_df["목표비중(%)"].sum()
        if total_ratio != 100:
            st.error(f"목표 비중의 합이 100%가 아닙니다. (현재: {total_ratio}%)")
            
        st.write("📊 **리밸런싱 실시간 연산 결과 (자동 환율 적용)**")
        
        res_df = edited_df.copy()
        target_shares_list = []
        for idx, row in res_df.iterrows():
            if row["현재가"] <= 0:
                target_shares_list.append(0)
                continue
                
            w = row["목표비중(%)"] / 100.0
            if base_curr == "원화 (KRW)":
                price_in_base = row["현재가"] if row["통화"] == "KRW" else row["현재가"] * EXCH_RATE
            else: 
                price_in_base = row["현재가"] if row["통화"] == "USD" else row["현재가"] / EXCH_RATE
                
            if price_in_base > 0:
                shares = np.floor((total_asset_budget * w) / price_in_base)
                target_shares_list.append(shares)
            else:
                target_shares_list.append(0)
                
        res_df["목표수량(주)"] = target_shares_list
        res_df["살 종목수(주)"] = res_df["목표수량(주)"] - res_df["보유수량(주)"].fillna(0)
        
        def fmt_price(row):
            if pd.isna(row['현재가']): return ""
            return f"{row['현재가']:,.0f}원" if row['통화'] == "KRW" else f"{row['현재가']:,.2f}$"

        disp_df = res_df[["자산명 (선택)", "티커 직접입력", "통화", "현재가", "보유수량(주)", "목표수량(주)", "살 종목수(주)"]].copy()
        disp_df['현재가(표시)'] = disp_df.apply(fmt_price, axis=1)
        disp_df = disp_df[["자산명 (선택)", "티커 직접입력", "통화", "현재가(표시)", "보유수량(주)", "목표수량(주)", "살 종목수(주)"]]
        
        def color_action(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}; font-weight: bold;'
        
        styled_df = disp_df.style.format({
            "보유수량(주)": "{:,.0f}주", 
            "목표수량(주)": "{:,.0f}주", 
            "살 종목수(주)": "{:,.0f}주"
        })
        
        if hasattr(styled_df, "map"): styled_df = styled_df.map(color_action, subset=["살 종목수(주)"])
        else: styled_df = styled_df.applymap(color_action, subset=["살 종목수(주)"])
            
        st.dataframe(styled_df, use_container_width=True)

    # --- 4. 자산배분 백테스트 (SPY, QQQ 동시 비교) ---
    with tab_backtest:
        st.write("과거 데이터를 기반으로 포트폴리오의 성과(총 수익률, CAGR, MDD, Sharpe)를 **SPY(S&P500), QQQ(나스닥 100)** 벤치마크와 비교 검증합니다.")
        
        date_col1, date_col2 = st.columns(2)
        bt_start = date_col1.date_input("백테스트 시작일", datetime.date.today() - datetime.timedelta(days=365*5))
        bt_end = date_col2.date_input("백테스트 종료일", datetime.date.today())
        
        if 'bt_df_base' not in st.session_state:
            st.session_state.bt_df_base = pd.DataFrame([
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "069500" in x), ""), "티커 직접입력": "", "투입비중(%)": 60.0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "308620" in x), ""), "티커 직접입력": "", "투입비중(%)": 40.0}
            ])
            
        bt_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 글로벌 전체 검색)", options=SEARCH_OPTIONS, width="large"),
            "티커 직접입력": st.column_config.TextColumn("티커 직접입력 (예: TQQQ)"),
            "투입비중(%)": st.column_config.NumberColumn("투입비중(%)", min_value=0.0, max_value=100.0)
        }
        
        st.caption("💡 **안내:** 자산을 추가하려면 표의 빈 칸(아래쪽)을 클릭하세요. 목록에 없는 종목은 '티커 직접입력' 칸에 작성하시면 됩니다.")
        edited_bt = st.data_editor(st.session_state.bt_df_base, num_rows="dynamic", column_config=bt_config, use_container_width=True, key="bt_editor")
        
        total_bt_ratio = edited_bt["투입비중(%)"].fillna(0).sum()
        if total_bt_ratio == 100:
            st.success(f"✅ **투입 비중 합계: {total_bt_ratio:.1f}%** (백테스트 실행 가능)")
        else:
            st.error(f"❌ **투입 비중 합계: {total_bt_ratio:.1f}%** (비중의 합을 100%로 맞춰주세요!)")
        
        if st.button("🚀 백테스트 실행", type="primary"):
            if total_bt_ratio != 100:
                st.error("투입비중의 합이 100%가 아닙니다. 표 아래의 합계를 확인해주세요.")
            else:
                with st.spinner("과거 데이터를 불러오고 성과를 분석 중입니다..."):
                    asset_weights = {}
                    for idx, row in edited_bt.iterrows():
                        w = row["투입비중(%)"] / 100.0
                        if pd.notna(w) and w > 0:
                            ticker = str(row.get("티커 직접입력", "")).strip()
                            if not ticker or ticker == "nan" or ticker == "None":
                                asset_str = row["자산명 (선택)"]
                                if asset_str and "(" in asset_str:
                                    ticker = asset_str.split("(")[-1].replace(")", "").strip()
                            
                            if ticker:
                                asset_weights[ticker] = asset_weights.get(ticker, 0) + w
                            
                    # 비교를 위해 SPY, QQQ 기본 추가
                    tickers_to_fetch = list(set(list(asset_weights.keys()) + ["SPY", "QQQ"]))
                    
                    try:
                        bt_data = yf.download(tickers_to_fetch, start=bt_start, end=bt_end, threads=False)
                        if 'Close' in bt_data.columns: bt_price = bt_data['Close']
                        else: bt_price = bt_data
                            
                        if isinstance(bt_price, pd.Series): bt_price = bt_price.to_frame(tickers_to_fetch[0])
                        bt_price = bt_price.ffill().dropna()
                        daily_ret = bt_price.pct_change().dropna()
                        
                        port_ret = pd.Series(0.0, index=daily_ret.index)
                        for tkr, weight in asset_weights.items():
                            if tkr in daily_ret.columns: port_ret += daily_ret[tkr] * weight
                                
                        spy_ret = daily_ret["SPY"] if "SPY" in daily_ret.columns else pd.Series(0.0, index=daily_ret.index)
                        qqq_ret = daily_ret["QQQ"] if "QQQ" in daily_ret.columns else pd.Series(0.0, index=daily_ret.index)
                        
                        port_cum = (1 + port_ret).cumprod() * 100
                        spy_cum = (1 + spy_ret).cumprod() * 100
                        qqq_cum = (1 + qqq_ret).cumprod() * 100
                        
                        def get_metrics(rets, cums):
                            days = len(rets)
                            if days < 2: return 0, 0, 0, 0
                            years = days / 252
                            total_return = (cums.iloc[-1] / 100) - 1
                            cagr = (cums.iloc[-1] / 100) ** (1 / years) - 1
                            roll_max = cums.cummax()
                            drawdowns = cums / roll_max - 1
                            mdd = drawdowns.min()
                            sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() != 0 else 0
                            return total_return, cagr, mdd, sharpe
                            
                        p_tot, p_cagr, p_mdd, p_sharpe = get_metrics(port_ret, port_cum)
                        s_tot, s_cagr, s_mdd, s_sharpe = get_metrics(spy_ret, spy_cum)
                        q_tot, q_cagr, q_mdd, q_sharpe = get_metrics(qqq_ret, qqq_cum)
                        
                        st.divider()
                        st.subheader("📊 백테스트 분석 결과")
                        
                        actual_start = port_cum.index[0].strftime('%Y년 %m월 %d일')
                        actual_end = port_cum.index[-1].strftime('%Y년 %m월 %d일')
                        st.markdown(f"""
                        <div style="background-color: rgba(79,142,247,0.12); border-left: 5px solid #4f8ef7; padding: 18px 24px; border-radius: 8px; margin-bottom: 28px;">
                            <span style="font-size: 1.1em; color: #e8eaf0; font-weight: 700;">🗓️ 실제 데이터 반영 기간: </span>
                            <span style="font-size: 1.2em; color: #4f8ef7; font-weight: 800; margin-left: 8px; letter-spacing: 0.5px;">{actual_start} &nbsp;➔&nbsp; {actual_end}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        html_table = f"""
                        <div style="background-color: #1e2130; padding: 20px; border-radius: 12px; border: 1px solid #2e3147; margin-bottom: 20px;">
                            <table style="width:100%; text-align:right; font-size:1em; border-collapse: collapse;">
                                <tr style="border-bottom: 2px solid #4f8ef7; color:#8b90a8;">
                                    <th style="text-align:left; padding:10px;">성과 지표</th>
                                    <th style="padding:10px; color:#4f8ef7;">전략 포트폴리오</th>
                                    <th style="padding:10px;">SPY (S&P 500)</th>
                                    <th style="padding:10px;">QQQ (NASDAQ)</th>
                                </tr>
                                <tr style="border-bottom: 1px solid #2e3147;">
                                    <td style="text-align:left; padding:12px; font-weight:bold; color:#e8eaf0;">총 누적 수익률</td>
                                    <td style="padding:12px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{p_tot*100:,.2f}%</td>
                                    <td style="padding:12px; color:#e8eaf0;">{s_tot*100:,.2f}%</td>
                                    <td style="padding:12px; color:#e8eaf0;">{q_tot*100:,.2f}%</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #2e3147;">
                                    <td style="text-align:left; padding:12px; font-weight:bold; color:#e8eaf0;">연평균 수익률 (CAGR)</td>
                                    <td style="padding:12px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{p_cagr*100:,.2f}%</td>
                                    <td style="padding:12px; color:#e8eaf0;">{s_cagr*100:,.2f}%</td>
                                    <td style="padding:12px; color:#e8eaf0;">{q_cagr*100:,.2f}%</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #2e3147;">
                                    <td style="text-align:left; padding:12px; font-weight:bold; color:#e74c3c; font-weight:bold; font-size:1.1em;">{p_mdd*100:,.2f}%</td>
                                    <td style="padding:12px; color:#8b90a8;">{s_mdd*100:,.2f}%</td>
                                    <td style="padding:12px; color:#8b90a8;">{q_mdd*100:,.2f}%</td>
                                </tr>
                                <tr>
                                    <td style="text-align:left; padding:12px; font-weight:bold; color:#e8eaf0;">위험조정수익률 (Sharpe)</td>
                                    <td style="padding:12px; color:#4f8ef7; font-weight:bold; font-size:1.1em;">{p_sharpe:.2f}</td>
                                    <td style="padding:12px; color:#8b90a8;">{s_sharpe:.2f}</td>
                                    <td style="padding:12px; color:#8b90a8;">{q_sharpe:.2f}</td>
                                </tr>
                            </table>
                        </div>
                        """
                        st.markdown(html_table, unsafe_allow_html=True)
                        
                        st.write("📈 **누적 자산 추이 비교 (초기 투자금 100 기준)**")
                        chart_df = pd.DataFrame({
                            "전략 포트폴리오": port_cum,
                            "SPY (미국 S&P 500)": spy_cum,
                            "QQQ (미국 나스닥)": qqq_cum
                        })
                        st.line_chart(chart_df)
                        
                    except Exception as e:
                        st.error(f"백테스트 진행 중 오류가 발생했습니다. 종목 코드나 날짜 범위를 다시 확인해주세요. (사유: {e})")

    # --- 5. 기대수익률 (ROE/PBR) 스마트 가치평가 및 DART 연동 ---
    with tab_roe:
        st.write("📊 **기업 가치 및 연평균 기대수익률(R) 스마트 연산기**")
        st.info("💡 종목을 검색하고 데이터 연동을 누르거나, **DART 재무제표 텍스트 파일**을 직접 올려서 더욱 정밀한 BPS 및 PBR, ROE를 추출할 수 있습니다.")
        
        uploaded_files = st.file_uploader("📁 DART 재무제표 텍스트(.txt) 업로드 (선택사항 / 다중 선택 가능)", type=['txt'], accept_multiple_files=True)

        def fetch_roe_data():
            sel = st.session_state.get("roe_search_box", "")
            if sel and "직접 입력" not in sel:
                tkr = sel.split("(")[-1].replace(")", "").strip()
                comp_name = sel.split("(")[0].strip()
                
                file_pbr_bps_found = False
                if uploaded_files:
                    eq_vals, ni_vals = parse_dart_files(uploaded_files, comp_name)
                    if eq_vals[0] != 0.0:
                        code = tkr.split('.')[0] if '.' in tkr else tkr
                        try:
                            krx_df = fdr.StockListing('KRX')
                            stock_row = krx_df[krx_df['Code'] == code]
                            if not stock_row.empty:
                                shares = float(stock_row['Stocks'].iloc[0])
                                price = float(stock_row['Close'].iloc[0])
                                if shares > 0 and price > 0:
                                    bps = eq_vals[0] / shares
                                    st.session_state.ui_pbr = round(price / bps, 2)
                                    st.session_state.ui_price = price
                                    file_pbr_bps_found = True
                        except: pass
                        
                        valid_roes = [(n/e)*100 for e, n in zip(eq_vals, ni_vals) if e != 0 and n != 0]
                        if valid_roes:
                            st.session_state.roe_val_3 = round(sum(valid_roes)/len(valid_roes), 2)
                            st.session_state.roe_val_5 = st.session_state.roe_val_3
                            st.session_state.roe_val_10 = st.session_state.roe_val_3
                
                if not file_pbr_bps_found:
                    pbr_v, roe3, roe5, roe10, price_v = get_pbr_roe_price(tkr)
                    st.session_state.roe_val_3 = round(roe3, 2)
                    st.session_state.roe_val_5 = round(roe5, 2)
                    st.session_state.roe_val_10 = round(roe10, 2)
                    st.session_state.ui_pbr = round(pbr_v, 2) if pbr_v > 0 else 1.0
                    st.session_state.ui_price = float(price_v)
                
                period = st.session_state.get("roe_period_box", "3년 평균 ROE")
                if period == "3년 평균 ROE": st.session_state.ui_roe = st.session_state.roe_val_3
                elif period == "5년 평균 ROE": st.session_state.ui_roe = st.session_state.roe_val_5
                else: st.session_state.ui_roe = st.session_state.roe_val_10
                
        def update_roe_from_period():
            period = st.session_state.get("roe_period_box", "3년 평균 ROE")
            if period == "3년 평균 ROE": st.session_state.ui_roe = st.session_state.get("roe_val_3", 15.0)
            elif period == "5년 평균 ROE": st.session_state.ui_roe = st.session_state.get("roe_val_5", 15.0)
            else: st.session_state.ui_roe = st.session_state.get("roe_val_10", 15.0)
        
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            st.selectbox("🔍 분석할 종목 검색", options=SEARCH_OPTIONS, key="roe_search_box")
        with sc2:
            st.write("") 
            st.button("🔄 재무 데이터 자동 연동", on_click=fetch_roe_data, use_container_width=True)

        st.divider()
        
        r1, r2, r3, r4 = st.columns(4)
        pbr = r1.number_input("현재 PBR (주가순자산비율)", step=0.01, key="ui_pbr")
        roe_period = r2.selectbox("적용 ROE 기준 선택", ["3년 평균 ROE", "5년 평균 ROE", "10년 평균 ROE"], key="roe_period_box", on_change=update_roe_from_period)
        roe = r2.number_input("해당 평균 ROE (%)", step=0.1, key="ui_roe")
        n_years = r3.number_input("가치평가 기준 연수 (N년)", value=10, step=1)
        curr_price = r4.number_input("현재 주가 (참고용)", step=100.0, key="ui_price")
        
        if pbr > 0 and n_years > 0:
            bps = curr_price / pbr if curr_price > 0 else 0
            future_value = bps * ((1 + (roe/100)) ** n_years)
            value_multiplier = future_value / curr_price if curr_price > 0 else 0
            
            if value_multiplier > 0:
                exp_return = (10 ** (np.log10(value_multiplier) / n_years) - 1) * 100
            else:
                exp_return = 0
                
            target_buy_price = future_value / ((1 + 0.15) ** n_years)
            
            st.markdown("### 🎯 **핵심 가치평가 분석 리포트**")
            
            res_c1, res_c2, res_c3 = st.columns(3)
            with res_c1:
                st.metric(f"📈 도출된 연평균 기대수익률", f"{exp_return:.2f}%")
            with res_c2:
                st.metric(f"🚀 {n_years}년 가치 승수", f"{value_multiplier:.2f} 배")
            with res_c3:
                st.metric(f"🔮 {n_years}년 후 예상 적정 가치", f"{future_value:,.0f} 원" if bps > 0 else "주가 입력 필요")
            
            if curr_price > 0 and bps > 0:
                discount_rate = (target_buy_price / curr_price - 1) * 100
                st.markdown(f"""
                <div style="background-color: #f8f9fa; border-left: 6px solid #2ecc71; padding: 20px 24px; border-radius: 8px; margin-top: 10px; border-top: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0; border-bottom: 1px solid #e0e0e0;">
                    <span style="font-size: 1.1em; color: #000000; font-weight: 700;">💡 연 15% 복리 수익률을 확보하기 위한 <span style="color:#1e8449;">최대 목표 매수가</span>:</span><br>
                    <span style="font-size: 1.6em; color: #000000; font-weight: 900; letter-spacing: 0.5px;">{target_buy_price:,.0f} 원</span>
                    <span style="font-size: 0.95em; color: #000000; font-weight: 600; margin-left: 10px;">(현재 주가 대비 {discount_rate:+.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)

            risks = []
            if pbr >= 3.0: risks.append("⚠️ **고평가 우려:** 현재 PBR이 3배 이상으로 자산 대비 주가 프리미엄이 높게 형성되어 있습니다.")
            if roe < 10.0: risks.append("⚠️ **수익성 부족:** 장기 평균 ROE가 10% 미만으로 자본 효율성이 다소 떨어지는 추세입니다.")
            if curr_price > target_buy_price: risks.append("⚠️ **단기 조정 리스크:** 현재 주가가 연 15% 수익을 달성하기 위한 적정 목표 매수가보다 고평가되어 있습니다.")
            if not risks: risks.append("✅ **안정성:** 재무 지표 상 특별한 과열이나 수익성 경고 신호가 감지되지 않았습니다.")
            
            st.markdown("### 🔍 **기업 재무제표 기반 투자 우려사항 점검**")
            for r in risks:
                st.write(r)

# ==========================================
# 2. 📊 동적 자산배분 대시보드
# ==========================================
elif app_mode == "📊 동적 자산배분 대시보드":
    st.subheader("💡 동적 자산배분 실시간 리밸런싱 대시보드")
    try:
        with st.spinner('금융 시장 데이터를 실시간 동기화 중입니다...'):
            data = load_financial_data(all_tickers)
            unrate_data = load_fred_data()
            
        month_data = data.resample('ME').last()
        
        if len(month_data) < 14:
            st.error("데이터가 부족합니다. (최소 14개월 필요)")
        else:
            st.write(f"📅 실시간 분석 기준일: **{month_data.index[-1].strftime('%Y년 %m월 %d일')}**")
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "📌 1. 밸런스 전략", "🚀 2. 미국밸런스 섹터 전략", 
                "🛡️ 3. LAA 전략", "⚡ 4. 한국형가속자산배분전략"
            ])
            
            v_tkrs = lambda tkrs: [t for t in tkrs if t in month_data.columns]
            
            with tab1:
                col1, col2 = st.columns([1, 1])
                buy1_prev, buy1_curr = {}, {}
                s1_off, s1_def = v_tkrs(strat1_off), v_tkrs(strat1_def)
                
                if "TIP" in month_data.columns:
                    tip_prev = get_baa_score(month_data["TIP"], -2)
                    if tip_prev > 0 and s1_off:
                        for a in pd.Series({a: get_baa_score(month_data[a], -2) for a in s1_off}).nlargest(4).index: buy1_prev[a] = "25.0%"
                    elif s1_def:
                        buy1_prev[pd.Series({a: get_baa_score(month_data[a], -2) for a in s1_def}).nlargest(1).index[0]] = "100.0%"
                        
                    tip_curr = get_baa_score(month_data["TIP"], -1)
                    if tip_curr > 0 and s1_off:
                        st.success(f"📈 [이번 달 시장 국면] 공격형 자산 매수장 (TIP 스코어: {tip_curr:.4f})")
                        for a in pd.Series({a: get_baa_score(month_data[a], -1) for a in s1_off}).nlargest(4).index: buy1_curr[a] = "25.0%"
                    elif s1_def:
                        st.warning(f"📉 [이번 달 시장 국면] 방어형 안전자산 대피장 (TIP 스코어: {tip_curr:.4f})")
                        buy1_curr[pd.Series({a: get_baa_score(month_data[a], -1) for a in s1_def}).nlargest(1).index[0]] = "100.0%"
                else:
                    st.error("⚠️ 야후 파이낸스에서 'TIP' 데이터를 불러오지 못해 1번 전략을 계산할 수 없습니다.")
                
                with col1:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    if buy1_prev: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1_prev.items()]))
                with col2:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    if buy1_curr: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1_curr.items()]))
                
                st.divider()
                render_dashboard_backtest_ui(1, month_data, data, unrate_data)
                st.divider()
                if buy1_curr: render_dashboard_rebalancer("1", buy1_curr, data)

            with tab2:
                col3, col4 = st.columns([1, 1])
                buy2_prev, buy2_curr = {}, {}
                s2_off, s2_def = v_tkrs(strat2_off), v_tkrs(strat2_def)
                
                if "TIP" in month_data.columns:
                    if tip_prev > 0 and s2_off:
                        for a in pd.Series({a: get_baa_score(month_data[a], -2) for a in s2_off}).nlargest(4).index: buy2_prev[a] = "25.0%"
                    elif s2_def:
                        buy2_prev[pd.Series({a: get_baa_score(month_data[a], -2) for a in s2_def}).nlargest(1).index[0]] = "100.0%"
                        
                    if tip_curr > 0 and s2_off:
                        st.success(f"📈 [이번 달 시장 국면] 공격형 자산 매수장 (TIP 스코어: {tip_curr:.4f})")
                        for a in pd.Series({a: get_baa_score(month_data[a], -1) for a in s2_off}).nlargest(4).index: buy2_curr[a] = "25.0%"
                    elif s2_def:
                        st.warning(f"📉 [이번 달 시장 국면] 방어형 안전자산 대피장 (TIP 스코어: {tip_curr:.4f})")
                        buy2_curr[pd.Series({a: get_baa_score(month_data[a], -1) for a in s2_def}).nlargest(1).index[0]] = "100.0%"
                
                with col3:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    if buy2_prev: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2_prev.items()]))
                with col4:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    if buy2_curr: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2_curr.items()]))
                
                st.divider()
                render_dashboard_backtest_ui(2, month_data, data, unrate_data)
                st.divider()
                if buy2_curr: render_dashboard_rebalancer("2", buy2_curr, data)

            with tab3:
                col5, col6 = st.columns([1, 1])
                buy3_prev, buy3_curr = {}, {}
                
                if "SPY" in data.columns and "UNRATE" in unrate_data.columns:
                    p_date = month_data.index[-2]
                    spy_prev = data[data.index <= p_date]['SPY'].iloc[-1]
                    spy_200_prev = data[data.index <= p_date]['SPY'].rolling(200).mean().iloc[-1]
                    ur_prev_df = unrate_data[unrate_data.index <= p_date]
                    ur_prev = ur_prev_df['UNRATE'].iloc[-1]
                    ur_12_prev = ur_prev_df['UNRATE'].rolling(12).mean().iloc[-1]
                    
                    for t in ["IWD", "GLD", "IEF"]: buy3_prev[t] = "25.0%"
                    if (spy_prev < spy_200_prev) and (ur_prev > ur_12_prev): buy3_prev["SHY"] = "25.0%"
                    else: buy3_prev["QQQ"] = "25.0%"
                    
                    spy_curr = data['SPY'].iloc[-1]
                    spy_200 = data['SPY'].rolling(200).mean().iloc[-1]
                    unrate_curr = unrate_data['UNRATE'].iloc[-1]
                    unrate_12 = unrate_data['UNRATE'].rolling(12).mean().iloc[-1]
                    
                    for t in ["IWD", "GLD", "IEF"]: buy3_curr[t] = "25.0%"
                    if (spy_curr < spy_200) and (unrate_curr > unrate_12):
                        st.warning("🚨 [이번 달 시장 국면] 불황장 (안전자산 타이밍) ➔ **SHY 매수**")
                        buy3_curr["SHY"] = "25.0%"
                    else:
                        st.info("☀️ [이번 달 시장 국면] 평시/회복기 (공격자산 타이밍) ➔ **QQQ 매수**")
                        buy3_curr["QQQ"] = "25.0%"
                else:
                    st.warning("⚠️ LAA 전략에 필요한 핵심 데이터(SPY 또는 실업률)를 야후 파이낸스에서 불러올 수 없습니다.")
                
                with col5:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    if buy3_prev: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3_prev.items()]))
                with col6:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    if buy3_curr: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3_curr.items()]))

                st.divider()
                render_dashboard_backtest_ui(3, month_data, data, unrate_data)
                st.divider()
                if buy3_curr: render_dashboard_rebalancer("3", buy3_curr, data)

            with tab4:
                col7, col8 = st.columns([1, 1])
                buy4_prev, buy4_curr = {} , {}
                s4_off, s4_def = v_tkrs(strat4_off), v_tkrs(strat4_def)
                
                if s4_off or s4_def:
                    max_sc_prev = pd.Series({a: get_aaa_score(month_data[a], -2) for a in s4_off}).max() if s4_off else -1
                    if max_sc_prev > 0 and s4_off:
                        buy4_prev[pd.Series({a: get_aaa_score(month_data[a], -2) for a in s4_off}).nlargest(1).index[0]] = "100.0%"
                    elif s4_def:
                        buy4_prev[pd.Series({a: month_data[a].iloc[-2]/month_data[a].iloc[-3] for a in s4_def}).nlargest(1).index[0]] = "100.0%"
                        
                    aaa_scores_curr = pd.Series({a: get_aaa_score(month_data[a], -1) for a in s4_off}) if s4_off else pd.Series(dtype=float)
                    max_sc_curr = aaa_scores_curr.max() if not aaa_scores_curr.empty else -1
                    
                    if max_sc_curr > 0 and s4_off:
                        st.success("📈 [이번 달 시장 국면] 공격형 자산 집중장")
                        buy4_curr[aaa_scores_curr.nlargest(1).index[0]] = "100.0%"
                    elif s4_def:
                        st.warning("📉 [이번 달 시장 국면] 방어형 자산 대피장")
                        buy4_curr[pd.Series({a: month_data[a].iloc[-1]/month_data[a].iloc[-2] for a in s4_def}).nlargest(1).index[0]] = "100.0%"
                else:
                    st.warning("⚠️ 야후 파이낸스에서 한국형 가속자산배분 ETF 데이터를 정상적으로 받아오지 못했습니다.")
                
                with col7:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    if buy4_prev: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4_prev.items()]))
                with col8:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    if buy4_curr: st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4_curr.items()]))

                st.divider()
                render_dashboard_backtest_ui(4, month_data, data, unrate_data)
                st.divider()
                if buy4_curr: render_dashboard_rebalancer("4", buy4_curr, data)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

# ==========================================
# ⚖️ 글로벌 법적 고지 및 면책사항 (Footer)
# ==========================================
st.divider()
footer_html = """
<div style='text-align: center; color: #8b90a8; font-size: 0.85em; padding: 20px 0; line-height: 1.6;'>
    <strong>⚖️ 법적 고지 및 면책사항 (Disclaimer)</strong><br>
    본 웹사이트(플랫폼)에서 제공하는 모든 정보, 데이터, 연산 결과는 투자 결정의 참고 용도로만 제공되며, 그 정확성이나 완전성을 보장하지 않습니다.<br>
    야후 파이낸스(Yahoo Finance), FRED, Naver, DART, CNN Fear & Greed 등 외부 통신망에서 제공되는 실시간 데이터는 시스템 환경에 따라 지연되거나 오류가 발생할 수 있습니다.<br>
    본 플랫폼의 제작 및 제공자는 사용자의 투자 결과에 대해 어떠한 법적, 도의적 책임도 지지 않습니다.<br> 
    <strong>모든 최종 투자 판단과 그에 따른 책임은 투자자 본인에게 있습니다.</strong>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
