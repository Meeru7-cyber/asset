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
# 🧭 금액 콤마 처리용 안전 변환 함수 & 콜백
# ==========================================
def safe_int(val):
    if isinstance(val, str):
        val = val.replace(",", "").strip()
    try:
        return int(float(val))
    except:
        return 0

def format_number_str(key):
    val = str(st.session_state[key]).replace(",", "").strip()
    try:
        if val == "": 
            st.session_state[key] = "0"
        else: 
            st.session_state[key] = f"{int(float(val)):,}"
    except ValueError:
        st.session_state[key] = "0"

if "budget_stock" not in st.session_state: st.session_state.budget_stock = "15,000,000"
if "budget_idx" not in st.session_state: st.session_state.budget_idx = "15,000,000"
if "budget_asset" not in st.session_state: st.session_state.budget_asset = "100,000,000"

# ==========================================
# 🧭 공통 기능: CNN Fear & Greed & 전체 종목 검색
# ==========================================
@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/json'
        }
        res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            score = int(data['fear_and_greed']['score'])
            rating = data['fear_and_greed']['rating']
            return score, rating
    except:
        pass
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
        
        all_kr = list(set(kospi_list + kosdaq_list + etf_list))
    except:
        all_kr = ["삼성전자 (005930.KS)", "KODEX 200 (069500.KS)", "TIGER 미국나스닥100 (133690.KS)"]
        
    us_majors = [
        "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Tesla (TSLA)", "Alphabet (GOOGL)",
        "SPDR S&P 500 (SPY)", "Invesco QQQ (QQQ)", "iShares 20+ Year Treasury (TLT)", "Schwab US Dividend (SCHD)"
    ]
    return ["직접 입력 (여기에 없는 종목)"] + sorted(all_kr) + us_majors

@st.cache_data(ttl=600)
def get_stock_info(ticker):
    if not ticker or ticker == "직접 입력": return 0.0, 0.0
    try:
        t = yf.Ticker(ticker)
        price = float(t.history(period="1d")['Close'].iloc[-1])
        info = t.info
        dividend = info.get('dividendRate', info.get('trailingAnnualDividendRate', 0.0))
        if dividend is None: dividend = 0.0
        return price, float(dividend)
    except:
        return 0.0, 0.0

# ==========================================
# 🎨 메인 타이틀 및 F&G 배너
# ==========================================
st.markdown("<h1 style='text-align: center;'>📊 프라이빗 투자 계산기</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b90a8; margin-top: -10px; margin-bottom: 30px;'>물타기 · 지수분할 · 기대수익률 · 자산배분 · 백테스트 통합 계산</p>", unsafe_allow_html=True)

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
app_mode = st.sidebar.radio("원하시는 기능을 선택하세요:", ["📊 동적 자산배분 대시보드", "🧮 프라이빗 투자 계산기"])
st.sidebar.caption("데이터 제공: Yahoo Finance, FRED, CNN")

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

@st.cache_data(ttl=14400)
def load_financial_data(tickers):
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date)
    if 'Close' in df.columns: df = df['Close']
    return df.dropna()

@st.cache_data(ttl=14400)
def load_fred_data():
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    return web.DataReader("UNRATE", "fred", start_date)

def get_baa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6, 9, 12]])

def get_aaa_score(series, idx=-1):
    return sum([(series.iloc[idx] - series.iloc[idx-m]) / series.iloc[idx-m] for m in [1, 3, 6]])


# ==========================================
# [모드 1] 동적 자산배분 대시보드
# ==========================================
if app_mode == "📊 동적 자산배분 대시보드":
    st.subheader("💡 동적 자산배분 실시간 리밸런싱 대시보드")
    try:
        with st.spinner('금융 시장 데이터를 실시간 동기화 중입니다...'):
            data = load_financial_data(all_tickers)
            unrate_data = load_fred_data()
            
        month_data = data.resample('ME').last()
        
        if len(month_data) < 13:
            st.error("데이터가 부족합니다.")
        else:
            st.write(f"📅 실시간 분석 기준일: **{month_data.index[-1].strftime('%Y년 %m월 %d일')}**")
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "📌 1. 밸런스 전략", "🚀 2. 미국밸런스 섹터 전략", 
                "🛡️ 3. LAA 전략", "⚡ 4. 한국형가속자산배분전략"
            ])
            tip_score = get_baa_score(month_data["TIP"])
            
            with tab1:
                col1, col2 = st.columns([1, 2])
                buy1 = {}
                with col1:
                    st.metric("🎗️ TIP 스코어", f"{tip_score:.4f}")
                    if tip_score > 0:
                        st.success("📈 공격형 자산 매수장")
                        top4 = pd.Series({a: get_baa_score(month_data[a]) for a in strat1_off}).nlargest(4)
                        for a in top4.index: buy1[a] = "25.0%"
                    else:
                        st.warning("📉 방어형 안전자산 대피장")
                        top1 = pd.Series({a: get_baa_score(month_data[a]) for a in strat1_def}).nlargest(1)
                        buy1[top1.index[0]] = "100.0%"
                with col2:
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1.items()]))

            with tab2:
                col3, col4 = st.columns([1, 2])
                buy2 = {}
                with col3:
                    st.metric("🎗️ TIP 스코어", f"{tip_score:.4f}")
                    if tip_score > 0:
                        st.success("📈 공격형 자산 매수장")
                        top4 = pd.Series({a: get_baa_score(month_data[a]) for a in strat2_off}).nlargest(4)
                        for a in top4.index: buy2[a] = "25.0%"
                    else:
                        st.warning("📉 방어형 안전자산 대피장")
                        top1 = pd.Series({a: get_baa_score(month_data[a]) for a in strat2_def}).nlargest(1)
                        buy2[top1.index[0]] = "100.0%"
                with col4:
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2.items()]))

            with tab3:
                col5, col6 = st.columns([1, 2])
                buy3 = {"IWD": "25.0%", "GLD": "25.0%", "IEF": "25.0%"}
                
                spy_curr = data['SPY'].iloc[-1]
                spy_200 = data['SPY'].rolling(200).mean().iloc[-1]
                unrate_curr = unrate_data['UNRATE'].iloc[-1]
                unrate_12 = unrate_data['UNRATE'].rolling(12).mean().iloc[-1]
                
                cond1 = spy_curr < spy_200
                cond2 = unrate_curr > unrate_12
                
                with col5:
                    if cond1 and cond2:
                        st.warning("🚨 불황장 ➔ **SHY 매수**")
                        buy3["SHY"] = "25.0%"
                    else:
                        st.info("☀️ 평시/회복기 ➔ **QQQ 매수**")
                        buy3["QQQ"] = "25.0%"
                with col6:
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3.items()]))

            with tab4:
                col7, col8 = st.columns([1, 2])
                buy4 = {}
                aaa_scores = pd.Series({a: get_aaa_score(month_data[a]) for a in strat4_off})
                max_sc = aaa_scores.max()
                
                with col7:
                    if max_sc > 0:
                        st.success("📈 공격형 자산 집중")
                        buy4[aaa_scores.nlargest(1).index[0]] = "100.0%"
                    else:
                        st.warning("📉 방어형 자산 대피")
                        def_scores = pd.Series({a: month_data[a].iloc[-1]/month_data[a].iloc[-2] for a in strat4_def})
                        buy4[def_scores.nlargest(1).index[0]] = "100.0%"
                with col8:
                    st.table(pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4.items()]))

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")


# ==========================================
# [모드 2] 프라이빗 투자 계산기
# ==========================================
elif app_mode == "🧮 프라이빗 투자 계산기":
    
    SEARCH_OPTIONS = get_all_search_options()
    
    tab_stock, tab_idx, tab_asset, tab_backtest, tab_roe = st.tabs([
        "📊 개별종목 물타기", "📉 지수 물타기", "🗂️ 자산배분 리밸런싱", "⏳ 자산배분 백테스트", "📈 기대수익률(R)"
    ])
    
    # --- 1. 개별종목 물타기 ---
    with tab_stock:
        st.write("개별종목 분할매수 스케줄 계산")
        
        # 신규: 사용자 안내 문구 추가
        st.info("💡 **안내:** 검색 후 종목의 현재가나 배당금이 외부 사정으로 인해 자동으로 나오지 않는다면, 해당 칸에 직접 **수동으로 입력해 주세요.**")
        
        selected_stock = st.selectbox("🔍 종목 검색 (한국 코스피/코스닥 전체 및 미국 주요 종목 지원)", options=SEARCH_OPTIONS, index=1)
        
        stock_ticker = ""
        if selected_stock == "직접 입력 (여기에 없는 종목)":
            stock_ticker = st.text_input("종목 코드 직접 입력 (예: 005930.KS, AAPL)")
        else:
            stock_ticker = selected_stock.split("(")[-1].replace(")", "").strip()
            
        fetched_price, fetched_div = get_stock_info(stock_ticker) if stock_ticker else (0.0, 0.0)
        
        c1, c2, c3, c4 = st.columns(4)
        budget_str = c1.text_input("총 투자 금액 (원)", key="budget_stock", on_change=format_number_str, args=("budget_stock",))
        
        # 신규: 선택된 종목의 Ticker를 key에 포함시켜, 종목이 바뀔 때마다 값을 강제로 새로고침 하도록 변경
        start_price_str = c2.text_input(
            "1회차 매수 가격 (자동입력)", 
            value=f"{int(fetched_price):,}" if fetched_price > 0 else "", 
            placeholder="안 나오면 수동 입력",
            key=f"sp_{stock_ticker}"
        )
        dividend_input_str = c3.text_input(
            "예상 주당 배당금 (자동입력)", 
            value=f"{int(fetched_div):,}" if fetched_div > 0 else "0",
            placeholder="안 나오면 수동 입력",
            key=f"div_{stock_ticker}"
        )
        steps = c4.number_input("분할 횟수", min_value=2, max_value=20, value=5)
        
        budget = safe_int(budget_str)
        start_price = safe_int(start_price_str)
        dividend_input = safe_int(dividend_input_str)
        
        st.divider()
        drop_type = st.radio("하락폭 설정", ["일괄 (매회 동일)", "직접 입력"], horizontal=True)
        
        drops = []
        if drop_type == "일괄 (매회 동일)":
            fixed_drop_str = st.text_input("회당 하락 금액 (원)", value="1,000")
            fixed_drop = safe_int(fixed_drop_str)
            drops = [fixed_drop] * (steps - 1)
        else:
            st.write("회차별 하락 금액 설정 (이전 회차 대비)")
            drop_cols = st.columns(steps - 1)
            for i in range(steps - 1):
                val_str = drop_cols[i].text_input(f"{i+1}➔{i+2}차", value="1,000", key=f"drop_{i}")
                drops.append(safe_int(val_str))
                
        if st.button("개별종목 계산하기", type="primary"):
            if start_price <= 0:
                st.error("❗ 매수 가격이 0원이거나 입력되지 않았습니다. 현재가를 수동으로 입력해 주세요.")
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
                    res.append({"회차": f"{i}차 ({i}배수)", "목표금액": int(target_amt), "매수가격": int(curr_price), "매수수량": shares, "체결금액": int(actual)})
                
                st.dataframe(pd.DataFrame(res).style.format({"목표금액": "{:,.0f}원", "매수가격": "{:,.0f}원", "체결금액": "{:,.0f}원", "매수수량": "{:,.0f}주"}), use_container_width=True)
                
                avg_price = int(t_spent/t_shares) if t_shares > 0 else 0
                yield_rate = (dividend_input / avg_price) * 100 if avg_price > 0 and dividend_input > 0 else 0.0
                st.success(f"**총 매수금액:** {t_spent:,.0f}원 | **평균단가:** {avg_price:,.0f}원 | **예상 배당률:** {yield_rate:.2f}% | **누적수량:** {t_shares:,.0f}주")

    # --- 2. 지수 물타기 ---
    with tab_idx:
        st.write("지수/ETF 분할매수 스케줄 계산")
        
        st.info("💡 **안내:** 검색 후 종목의 현재가가 외부 사정으로 인해 자동으로 나오지 않는다면, 직접 **수동으로 입력해 주세요.**")
        
        default_idx = next((i for i, x in enumerate(SEARCH_OPTIONS) if "069500" in x), 1)
        selected_idx = st.selectbox("🔍 지수/ETF 검색", options=SEARCH_OPTIONS, index=default_idx, key="idx_search") 
        
        idx_ticker = ""
        if selected_idx == "직접 입력 (여기에 없는 종목)":
            idx_ticker = st.text_input("ETF 코드 직접 입력", key="idx_custom")
        else:
            idx_ticker = selected_idx.split("(")[-1].replace(")", "").strip()
            
        fetched_idx_price, _ = get_stock_info(idx_ticker) if idx_ticker else (0.0, 0.0)

        i1, i2, i3, i4 = st.columns(4)
        
        idx_budget_str = i1.text_input("지수 총 투자 금액 (원)", key="budget_idx", on_change=format_number_str, args=("budget_idx",))
        
        # 신규: 인덱스 티커 기반 동적 키 지정
        idx_start_str = i2.text_input(
            "첫 매수 지수/단가 (자동입력)", 
            value=f"{int(fetched_idx_price):,}" if fetched_idx_price > 0 else "",
            placeholder="안 나오면 수동 입력",
            key=f"idx_p_{idx_ticker}"
        )
        idx_drop = i3.number_input("구간별 하락률 (%)", value=5.0, step=0.5)
        idx_steps = i4.number_input("지수 분할 횟수", min_value=2, max_value=20, value=5)
        
        idx_budget = safe_int(idx_budget_str)
        idx_start = safe_int(idx_start_str)
        
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
                    res_idx.append({"회차": f"{i}차 (-{idx_drop*(i-1)}%)", "목표금액": int(target_amt), "매수지수(원)": int(curr_idx), "매수수량": shares, "체결금액": int(actual)})
                
                st.dataframe(pd.DataFrame(res_idx).style.format({"목표금액": "{:,.0f}원", "매수지수(원)": "{:,.0f}원", "체결금액": "{:,.0f}원", "매수수량": "{:,.0f}주"}), use_container_width=True)
                st.success(f"**총 매수금액:** {t_spent_idx:,.0f}원 | **평균단가:** {int(t_spent_idx/t_shares_idx) if t_shares_idx > 0 else 0:,.0f}원 | **누적수량:** {t_shares_idx:,.0f}주")

    # --- 3. 자산배분 리밸런싱 ---
    with tab_asset:
        st.write("포트폴리오 비중 조절 (리밸런싱) 계산기")
        
        total_asset_budget_str = st.text_input("총 투자 운용 금액 (원)", key="budget_asset", on_change=format_number_str, args=("budget_asset",))
        total_asset_budget = safe_int(total_asset_budget_str)
        
        if 'asset_df_base' not in st.session_state:
            st.session_state.asset_df_base = pd.DataFrame([
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "069500" in x), "직접 입력"), "현재가(원)": 35000, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "360750" in x), "직접 입력"), "현재가(원)": 15000, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "308620" in x), "직접 입력"), "현재가(원)": 11000, "목표비중(%)": 20.0, "보유수량(주)": 0},
                {"자산명 (선택)": next((x for x in SEARCH_OPTIONS if "411060" in x), "직접 입력"), "현재가(원)": 13000, "목표비중(%)": 20.0, "보유수량(주)": 0}
            ])
            
        column_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 전체 검색)", options=SEARCH_OPTIONS, width="large"),
            "현재가(원)": st.column_config.NumberColumn("현재가(원)", format="%d"),
            "목표비중(%)": st.column_config.NumberColumn("목표비중(%)", min_value=0.0, max_value=100.0),
            "보유수량(주)": st.column_config.NumberColumn("보유수량(주)", min_value=0, format="%d")
        }

        st.caption("💡 자산을 추가하려면 표의 빈 칸(아래쪽)을 클릭하고, 삭제하려면 맨 왼쪽 칸(인덱스)을 클릭 후 휴지통 아이콘(또는 Delete 키)을 누르세요.")
        edited_df = st.data_editor(st.session_state.asset_df_base, num_rows="dynamic", column_config=column_config, use_container_width=True, key="asset_editor")
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            if st.button("🔄 현재가 일괄 업데이트"):
                with st.spinner("현재가를 실시간으로 조회중입니다..."):
                    updated_df = edited_df.copy()
                    for idx, row in updated_df.iterrows():
                        asset_str = row["자산명 (선택)"]
                        if asset_str and "(" in asset_str:
                            ticker = asset_str.split("(")[-1].replace(")", "").strip()
                            price, _ = get_stock_info(ticker)
                            if price > 0:
                                updated_df.at[idx, "현재가(원)"] = int(price)
                    st.session_state.asset_df_base = updated_df
                    st.rerun()

        total_ratio = edited_df["목표비중(%)"].sum()
        if total_ratio != 100:
            st.error(f"목표 비중의 합이 100%가 아닙니다. (현재: {total_ratio}%)")
            
        st.write("📊 **리밸런싱 실시간 연산 결과 (자동 연동)**")
        result_df = edited_df.copy()
        
        result_df["목표수량(주)"] = np.floor((total_asset_budget * (result_df["목표비중(%)"]/100)) / result_df["현재가(원)"]).replace([np.inf, -np.inf, np.nan], 0)
        result_df["살 종목수(주)"] = result_df["목표수량(주)"] - result_df["보유수량(주)"]
        
        def color_action(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}; font-weight: bold;'
        
        styled_df = result_df[["자산명 (선택)", "현재가(원)", "보유수량(주)", "목표수량(주)", "살 종목수(주)"]].style.format({
            "현재가(원)": "{:,.0f}원", 
            "보유수량(주)": "{:,.0f}주", 
            "목표수량(주)": "{:,.0f}주", 
            "살 종목수(주)": "{:,.0f}주"
        })
        
        if hasattr(styled_df, "map"):
            styled_df = styled_df.map(color_action, subset=["살 종목수(주)"])
        else:
            styled_df = styled_df.applymap(color_action, subset=["살 종목수(주)"])
            
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
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 전체 검색)", options=SEARCH_OPTIONS, width="large"),
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
                        bt_data = yf.download(tickers_to_fetch, start=bt_start, end=bt_end)
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

    # --- 5. 기대수익률 (ROE/PBR) ---
    with tab_roe:
        st.write("연평균 기대수익률(R) 역산 도출")
        st.latex(r"R = \frac{1 + ROE}{PBR^{\frac{1}{n}}} - 1")
        
        r1, r2, r3 = st.columns(3)
        pbr = r1.number_input("PBR (주가순자산비율)", value=1.20, step=0.01)
        roe = r2.number_input("ROE (%)", value=15.0, step=0.1)
        n_years = r3.number_input("투자 기간 (N년)", value=10, step=1)
        
        if pbr > 0 and n_years > 0:
            exp_return = (((1 + (roe/100)) / (pbr ** (1/n_years))) - 1) * 100
            if exp_return >= 15:
                st.success(f"🎉 **도출된 연평균 기대수익률:** {exp_return:.2f}% (우수)")
            else:
                st.info(f"📊 **도출된 연평균 기대수익률:** {exp_return:.2f}%")


# ==========================================
# ⚖️ 글로벌 법적 고지 및 면책사항 (Footer)
# ==========================================
st.divider()
footer_html = """
<div style='text-align: center; color: #8b90a8; font-size: 0.85em; padding: 20px 0; line-height: 1.6;'>
    <strong>⚖️ 법적 고지 및 면책사항 (Disclaimer)</strong><br>
    본 웹사이트(플랫폼)에서 제공하는 모든 정보, 데이터, 연산 결과는 투자 결정의 참고 용도로만 제공되며, 그 정확성이나 완전성을 보장하지 않습니다.<br>
    야후 파이낸스(Yahoo Finance), FRED, CNN Fear & Greed 등 외부 통신망에서 제공되는 실시간 데이터는 시스템 환경에 따라 지연되거나 오류가 발생할 수 있습니다.<br>
    본 플랫폼의 제작 및 제공자는 사용자의 투자 결과에 대해 어떠한 법적, 도의적 책임도 지지 않습니다.<br> 
    <strong>모든 최종 투자 판단과 그에 따른 책임은 투자자 본인에게 있습니다.</strong>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
