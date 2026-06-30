import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import pandas_datareader.data as web
import requests
import FinanceDataReader as fdr

# ==========================================
# 🔐 비밀번호 인증 기능
# ==========================================
def check_password():
    """비밀번호 인증을 위한 함수"""
    def password_entered():
        if st.session_state["password"] == "1234":  # 여기에 원하시는 비번을 입력하세요
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 비번 저장 안되게 삭제
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 첫 접속 시 입력창 표시
        st.text_input("접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # 비번 틀렸을 때
        st.text_input("접속 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
        st.error("비밀번호가 틀렸습니다.")
        return False
    else:
        # 인증 성공
        return True

# 인증이 안 되었다면 여기서 멈춤
if not check_password():
    st.stop()


# 페이지 기본 설정
st.set_page_config(page_title="프라이빗 통합 투자 플랫폼", layout="wide")

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
    try:
        return float(val)
    except:
        return 0.0

def format_number_str(key):
    val = str(st.session_state[key]).replace(",", "").strip()
    try:
        if val == "": 
            st.session_state[key] = "0"
        else:
            f_val = float(val)
            if f_val.is_integer():
                st.session_state[key] = f"{int(f_val):,}"
            else:
                st.session_state[key] = f"{f_val:,.2f}"
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
    """실시간 원/달러 환율 추출"""
    try:
        t = yf.Ticker("KRW=X", session=yf_session)
        price = float(t.history(period="1d")['Close'].iloc[-1])
        return price if price > 500 else 1350.0
    except:
        return 1350.0

def detect_currency(ticker):
    """티커를 기반으로 국가/통화를 자동 인식"""
    if not ticker or "직접 입력" in ticker: return "KRW"
    if ticker.endswith('.KS') or ticker.endswith('.KQ'): return "KRW"
    if ticker.isalpha(): return "USD"
    return "KRW"

@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=yf_session.headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return int(data['fear_and_greed']['score']), data['fear_and_greed']['rating']
    except: pass
    return None, None

@st.cache_data(ttl=86400)
def get_all_search_options():
    try:
        kospi = fdr.StockListing('KOSPI')
        kospi_list = (kospi['Name'] + " (" + kospi['Code'] + ".KS)").tolist()
        kosdaq = fdr.StockListing('KOSDAQ')
        kosdaq_list = (kosdaq['Name'] + " (" + kosdaq['Code'] + ".KQ)").tolist()
        etf = fdr.StockListing('ETF/KR')
        etf_list = (etf['Name'] + " (" + etf['Symbol'] + ".KS)").tolist()
        
        sp500 = fdr.StockListing('S&P500')
        sp500_list = (sp500['Name'] + " (" + sp500['Symbol'] + ")").tolist()
        nasdaq = fdr.StockListing('NASDAQ')
        nasdaq_list = (nasdaq['Name'] + " (" + nasdaq['Symbol'] + ")").tolist()
        nyse = fdr.StockListing('NYSE')
        nyse_list = (nyse['Name'] + " (" + nyse['Symbol'] + ")").tolist()
        all_auto = list(set(kospi_list + kosdaq_list + etf_list + sp500_list + nasdaq_list + nyse_list))
    except:
        all_auto = ["삼성전자 (005930.KS)", "KODEX 200 (069500.KS)", "ACE KRX금현물 (411060.KS)"]
        
    us_etfs_and_commodities = [
        "SPDR S&P 500 ETF (SPY)", "Invesco QQQ Trust (QQQ)", "Vanguard S&P 500 ETF (VOO)", "Invesco NASDAQ 100 ETF (QQQM)",
        "Vanguard Total Stock Market (VTI)", "iShares 20+ Year Treasury Bond (TLT)", "iShares 7-10 Year Treasury Bond (IEF)", 
        "iShares 1-3 Year Treasury Bond (SHY)", "SPDR Bloomberg 1-3 Month T-Bill (BIL)", 
        "ProShares Ultra QQQ (QLD)", "ProShares UltraPro QQQ (TQQQ)", "ProShares UltraPro Short QQQ (SQQQ)",
        "Direxion Daily Semiconductor Bull 3X (SOXL)", "Direxion Daily Semiconductor Bear 3X (SOXS)",
        "SPDR Gold Shares (GLD)", "Invesco DB Commodity Tracking (DBC)", "United States Oil Fund (USO)", 
        "Technology Select Sector SPDR (XLK)", "Health Care Select Sector SPDR (XLV)", "Financial Select Sector SPDR (XLF)", 
        "iShares Semiconductor ETF (SOXX)", "VanEck Semiconductor ETF (SMH)", "Schwab US Dividend Equity ETF (SCHD)"
    ]
    combined = list(set(all_auto + us_etfs_and_commodities))
    return ["직접 입력 (여기에 없는 종목)"] + sorted(combined)

@st.cache_data(ttl=600)
def get_stock_info(ticker):
    if not ticker or ticker == "직접 입력": return 0.0, 0.0
    price = 0.0
    dividend = 0.0
    
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        code = ticker.split('.')[0]
        try:
            res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/basic", headers=yf_session.headers, timeout=3)
            if res.status_code == 200:
                price = float(res.json()['result']['closePrice'].replace(',', ''))
        except: pass
        
    try:
        t = yf.Ticker(ticker, session=yf_session)
        if price == 0.0:
            hist = t.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
        info = t.info
        # 배당금 조회 개선 (누락 시 0.0으로 안전하게 반환)
        div = info.get('dividendRate')
        if div is None:
            div = info.get('trailingAnnualDividendRate', 0.0)
        dividend = float(div) if div is not None else 0.0
    except:
        pass
        
    return price, dividend

@st.cache_data(ttl=3600)
def get_pbr_roe_price(ticker):
    if not ticker or "직접 입력" in ticker: return 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        t = yf.Ticker(ticker, session=yf_session)
        hist = t.history(period="1d")
        price = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
        
        pbr = 0.0
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            code = ticker.split('.')[0]
            try:
                res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/basic", headers=yf_session.headers, timeout=3)
                if res.status_code == 200:
                    pbr = float(res.json()['result']['pbr'])
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
    except:
        return 1.0, 0.0, 0.0, 0.0, 0.0

@st.cache_data(ttl=14400)
def load_financial_data(tickers):
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date, session=yf_session)
    if 'Close' in df.columns: df = df['Close']
    return df.ffill().dropna(how='all')

@st.cache_data(ttl=14400)
def load_fred_data():
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    return web.DataReader("UNRATE", "fred", start_date)

def get_baa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6, 9, 12]])

def get_aaa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6]])


# ==========================================
# 🧮 대시보드 리밸런싱 렌더링 함수
# ==========================================
def render_dashboard_rebalancer(strat_id, buy_dict, data_df):
    st.write("#### 🧮 전략 맞춤형 실시간 리밸런싱 계산기")
    
    b_col1, b_col2 = st.columns([1, 3])
    budget_key = f"budget_dash{strat_id}"
    budget_str = b_col1.text_input("총 투자 운용 금액 (원)", key=budget_key, on_change=format_number_str, args=(budget_key,))
    budget = safe_float(budget_str)
    
    df_list = []
    for tkr, w in buy_dict.items():
        price = 0.0
        if tkr in data_df.columns:
            price = float(data_df[tkr].iloc[-1])
        if price == 0.0 or pd.isna(price):
            price, _ = get_stock_info(tkr)
            
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
all_tickers = list(set(strat1_off + strat1_def + strat2_off + strat2_def + laa_assets + strat4_off + strat4_def + ["TIP"]))

# 통화 표기 유틸리티
def get_fmt(val, curr):
    if val == 0: return ""
    return f"{int(val):,}" if curr == "KRW" else f"{val:.2f}"

# ==========================================
# [모드 1] 🧮 프라이빗 투자 계산기
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
        
        # 통화 단위 자동 설정 및 수동 오버라이드
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
                
        if st.button("개별종목 계산하기", type="primary"):
            if start_price <= 0:
                st.error("❗ 매수 가격이 0이거나 입력되지 않았습니다. 현재가를 수동으로 입력해 주세요.")
            else:
                w_sum = (steps * (steps + 1)) / 2
                res, t_spent, t_shares = [], 0, 0
                curr_price = start_price
                
                for i in range(1, steps + 1):
                    target_amt = budget * (i / w_sum)
                    if i > 1: curr_price -= drops[i-2]
                    if curr_price <= 0: break
                    
                    shares = int(target_amt / curr_price)
                    actual = shares * curr_price
                    t_spent += actual
                    t_shares += shares
                    res.append({"회차": f"{i}차 ({i}배수)", "목표금액": target_amt, "매수가격": curr_price, "매수수량": shares, "체결금액": actual})
                
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
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "069500" in x), "직접 입력"), "통화": "KRW", "현재가": 35000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "360750" in x), "직접 입력"), "통화": "KRW", "현재가": 15000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "308620" in x), "직접 입력"), "통화": "KRW", "현재가": 11000.0, "목표비중(%)": 20.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "411060" in x), "직접 입력"), "통화": "KRW", "현재가": 13000.0, "목표비중(%)": 20.0, "보유수량(주)": 0}
            ])
            
        column_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 글로벌 전체 검색)", options=SEARCH_OPTIONS, width="large"),
            "통화": st.column_config.SelectboxColumn("통화", options=["KRW", "USD"]),
            "현재가": st.column_config.NumberColumn("현재가", format="%.2f"),
            "목표비중(%)": st.column_config.NumberColumn("목표비중(%)", min_value=0.0, max_value=100.0),
            "보유수량(주)": st.column_config.NumberColumn("보유수량(주)", min_value=0, format="%d")
        }

        st.caption("💡 자산을 추가하려면 표의 빈 칸(아래쪽)을 클릭하고, 삭제하려면 맨 왼쪽 칸(인덱스)을 클릭 후 휴지통 아이콘(또는 Delete 키)을 누르세요. 미국/한국 자산이 섞여도 환율이 자동 적용되어 '살 종목수'가 계산됩니다.")
        edited_df = st.data_editor(st.session_state.asset_df_base, num_rows="dynamic", column_config=column_config, use_container_width=True, key="asset_editor")
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            if st.button("🔄 현재가 및 통화 일괄 업데이트"):
                with st.spinner("현재가 및 통화 설정을 실시간으로 조회중입니다..."):
                    updated_df = edited_df.copy()
                    for idx, row in updated_df.iterrows():
                        asset_str = row["자산명 (선택)"]
                        if asset_str and "(" in asset_str:
                            ticker = asset_str.split("(")[-1].replace(")", "").strip()
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
        
        # 목표 수량 산출 (환율 변환)
        res_df = edited_df.copy()
        
        # 총 예산을 해당 종목의 통화로 맞춰서 수량 도출
        # 만약 budget이 KRW이고, 종목이 USD라면 -> target_amount_krw / (price_usd * exch_rate)
        # 만약 budget이 USD이고, 종목이 KRW라면 -> target_amount_usd / (price_krw / exch_rate)
        
        target_shares_list = []
        for idx, row in res_df.iterrows():
            if row["현재가"] <= 0:
                target_shares_list.append(0)
                continue
                
            w = row["목표비중(%)"] / 100.0
            
            # 자산의 가격을 기준 통화(Base Currency)로 변환
            if base_curr == "원화 (KRW)":
                price_in_base = row["현재가"] if row["통화"] == "KRW" else row["현재가"] * EXCH_RATE
            else: # 달러 기준
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

        disp_df = res_df[["자산명 (선택)", "통화", "현재가", "보유수량(주)", "목표수량(주)", "살 종목수(주)"]].copy()
        disp_df['현재가(표시)'] = disp_df.apply(fmt_price, axis=1)
        disp_df = disp_df[["자산명 (선택)", "통화", "현재가(표시)", "보유수량(주)", "목표수량(주)", "살 종목수(주)"]]
        
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

    # --- 4. 자산배분 백테스트 ---
    with tab_backtest:
        st.write("과거 데이터를 기반으로 포트폴리오의 성과(총 수익률, CAGR, MDD, Sharpe)를 S&P500(SPY)과 비교 검증합니다.")
        
        date_col1, date_col2 = st.columns(2)
        bt_start = date_col1.date_input("백테스트 시작일", datetime.date.today() - datetime.timedelta(days=365*5))
        bt_end = date_col2.date_input("백테스트 종료일", datetime.date.today())
        
        if 'bt_df_base' not in st.session_state:
            st.session_state.bt_df_base = pd.DataFrame([
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "069500" in x), ""), "투입비중(%)": 60.0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "308620" in x), ""), "투입비중(%)": 40.0}
            ])
            
        bt_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 글로벌 전체 검색)", options=SEARCH_OPTIONS, width="large"),
            "투입비중(%)": st.column_config.NumberColumn("투입비중(%)", min_value=0.0, max_value=100.0)
        }
        
        st.caption("💡 자산을 추가하려면 표의 빈 칸(아래쪽)을 클릭하고, 삭제하려면 맨 왼쪽 칸(인덱스)을 클릭 후 휴지통 아이콘(또는 Delete 키)을 누르세요.")
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
                        asset_str = row["자산명 (선택)"]
                        w = row["투입비중(%)"] / 100.0
                        if pd.notna(w) and w > 0 and asset_str and "(" in asset_str:
                            tkr = asset_str.split("(")[-1].replace(")", "").strip()
                            asset_weights[tkr] = asset_weights.get(tkr, 0) + w
                            
                    tickers_to_fetch = list(set(list(asset_weights.keys()) + ["SPY"]))
                    
                    try:
                        bt_data = yf.download(tickers_to_fetch, start=bt_start, end=bt_end, session=yf_session)
                        if 'Close' in bt_data.columns:
                            bt_price = bt_data['Close']
                        else:
                            bt_price = bt_data
                            
                        if isinstance(bt_price, pd.Series):
                            bt_price = bt_price.to_frame(tickers_to_fetch[0])
                            
                        bt_price = bt_price.ffill().dropna()
                        daily_ret = bt_price.pct_change().dropna()
                        
                        port_ret = pd.Series(0.0, index=daily_ret.index)
                        for tkr, weight in asset_weights.items():
                            if tkr in daily_ret.columns:
                                port_ret += daily_ret[tkr] * weight
                                
                        spy_ret = daily_ret["SPY"] if "SPY" in daily_ret.columns else pd.Series(0.0, index=daily_ret.index)
                        
                        port_cum = (1 + port_ret).cumprod() * 100
                        spy_cum = (1 + spy_ret).cumprod() * 100
                        
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
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("총 누적 수익률", f"{p_tot*100:.2f}%", f"SPY 벤치마크: {s_tot*100:.2f}%")
                        m2.metric("연평균 수익률 (CAGR)", f"{p_cagr*100:.2f}%", f"SPY 벤치마크: {s_cagr*100:.2f}%")
                        m3.metric("최대 낙폭 (MDD)", f"{p_mdd*100:.2f}%", f"SPY 벤치마크: {s_mdd*100:.2f}%", delta_color="inverse")
                        m4.metric("위험조정수익률 (Sharpe)", f"{p_sharpe:.2f}", f"SPY 벤치마크: {s_sharpe:.2f}")
                        
                        st.write("📈 **누적 자산 추이 비교 (초기 투자금 100 기준)**")
                        chart_df = pd.DataFrame({
                            "내 포트폴리오": port_cum,
                            "SPY (미국 S&P 500)": spy_cum
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

# ----------------------------------------
# 2. 📊 동적 자산배분 대시보드
# ----------------------------------------
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
            tip_score = get_baa_score(month_data["TIP"])
            
            with tab1:
                col1, col2 = st.columns([1, 1])
                buy1_prev, buy1_curr = {}, {}
                
                tip_prev = get_baa_score(month_data["TIP"], -2)
                if tip_prev > 0:
                    for a in pd.Series({a: get_baa_score(month_data[a], -2) for a in strat1_off}).nlargest(4).index: buy1_prev[a] = "25.0%"
                else:
                    buy1_prev[pd.Series({a: get_baa_score(month_data[a], -2) for a in strat1_def}).nlargest(1).index[0]] = "100.0%"
                    
                tip_curr = get_baa_score(month_data["TIP"], -1)
                if tip_curr > 0:
                    st.success(f"📈 [이번 달 시장 국면] 공격형 자산 매수장 (TIP 스코어: {tip_curr:.4f})")
                    for a in pd.Series({a: get_baa_score(month_data[a], -1) for a in strat1_off}).nlargest(4).index: buy1_curr[a] = "25.0%"
                else:
                    st.warning(f"📉 [이번 달 시장 국면] 방어형 안전자산 대피장 (TIP 스코어: {tip_curr:.4f})")
                    buy1_curr[pd.Series({a: get_baa_score(month_data[a], -1) for a in strat1_def}).nlargest(1).index[0]] = "100.0%"
                
                with col1:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1_prev.items()]))
                with col2:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1_curr.items()]))
                    
                st.divider()
                render_dashboard_rebalancer("1", buy1_curr, data)

            with tab2:
                col3, col4 = st.columns([1, 1])
                buy2_prev, buy2_curr = {}, {}
                
                if tip_prev > 0:
                    for a in pd.Series({a: get_baa_score(month_data[a], -2) for a in strat2_off}).nlargest(4).index: buy2_prev[a] = "25.0%"
                else:
                    buy2_prev[pd.Series({a: get_baa_score(month_data[a], -2) for a in strat2_def}).nlargest(1).index[0]] = "100.0%"
                    
                if tip_curr > 0:
                    st.success(f"📈 [이번 달 시장 국면] 공격형 자산 매수장 (TIP 스코어: {tip_curr:.4f})")
                    for a in pd.Series({a: get_baa_score(month_data[a], -1) for a in strat2_off}).nlargest(4).index: buy2_curr[a] = "25.0%"
                else:
                    st.warning(f"📉 [이번 달 시장 국면] 방어형 안전자산 대피장 (TIP 스코어: {tip_curr:.4f})")
                    buy2_curr[pd.Series({a: get_baa_score(month_data[a], -1) for a in strat2_def}).nlargest(1).index[0]] = "100.0%"
                
                with col3:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2_prev.items()]))
                with col4:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2_curr.items()]))
                    
                st.divider()
                render_dashboard_rebalancer("2", buy2_curr, data)

            with tab3:
                col5, col6 = st.columns([1, 1])
                buy3_prev = {"IWD": "25.0%", "GLD": "25.0%", "IEF": "25.0%"}
                buy3_curr = {"IWD": "25.0%", "GLD": "25.0%", "IEF": "25.0%"}
                
                p_date = month_data.index[-2]
                spy_prev = data[data.index <= p_date]['SPY'].iloc[-1]
                spy_200_prev = data[data.index <= p_date]['SPY'].rolling(200).mean().iloc[-1]
                ur_prev_df = unrate_data[unrate_data.index <= p_date]
                ur_prev = ur_prev_df['UNRATE'].iloc[-1]
                ur_12_prev = ur_prev_df['UNRATE'].rolling(12).mean().iloc[-1]
                
                if (spy_prev < spy_200_prev) and (ur_prev > ur_12_prev): buy3_prev["SHY"] = "25.0%"
                else: buy3_prev["QQQ"] = "25.0%"
                
                spy_curr = data['SPY'].iloc[-1]
                spy_200 = data['SPY'].rolling(200).mean().iloc[-1]
                unrate_curr = unrate_data['UNRATE'].iloc[-1]
                unrate_12 = unrate_data['UNRATE'].rolling(12).mean().iloc[-1]
                
                if (spy_curr < spy_200) and (unrate_curr > unrate_12):
                    st.warning("🚨 [이번 달 시장 국면] 불황장 (안전자산 타이밍) ➔ **SHY 매수**")
                    buy3_curr["SHY"] = "25.0%"
                else:
                    st.info("☀️ [이번 달 시장 국면] 평시/회복기 (공격자산 타이밍) ➔ **QQQ 매수**")
                    buy3_curr["QQQ"] = "25.0%"
                
                with col5:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3_prev.items()]))
                with col6:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3_curr.items()]))

                st.divider()
                render_dashboard_rebalancer("3", buy3_curr, data)

            with tab4:
                col7, col8 = st.columns([1, 1])
                buy4_prev, buy4_curr = {} , {}
                
                max_sc_prev = pd.Series({a: get_aaa_score(month_data[a], -2) for a in strat4_off}).max()
                if max_sc_prev > 0:
                    buy4_prev[pd.Series({a: get_aaa_score(month_data[a], -2) for a in strat4_off}).nlargest(1).index[0]] = "100.0%"
                else:
                    buy4_prev[pd.Series({a: month_data[a].iloc[-2]/month_data[a].iloc[-3] for a in strat4_def}).nlargest(1).index[0]] = "100.0%"
                    
                aaa_scores_curr = pd.Series({a: get_aaa_score(month_data[a], -1) for a in strat4_off})
                max_sc_curr = aaa_scores_curr.max()
                if max_sc_curr > 0:
                    st.success("📈 [이번 달 시장 국면] 공격형 자산 집중장")
                    buy4_curr[aaa_scores_curr.nlargest(1).index[0]] = "100.0%"
                else:
                    st.warning("📉 [이번 달 시장 국면] 방어형 자산 대피장")
                    buy4_curr[pd.Series({a: month_data[a].iloc[-1]/month_data[a].iloc[-2] for a in strat4_def}).nlargest(1).index[0]] = "100.0%"
                
                with col7:
                    st.write(f"🔙 **지난달 투자 비중 ({month_data.index[-2].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4_prev.items()]))
                with col8:
                    st.write(f"🎯 **이번 달 목표 비중 ({month_data.index[-1].strftime('%m월')} 기준)**")
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4_curr.items()]))

                st.divider()
                render_dashboard_rebalancer("4", buy4_curr, data)

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
