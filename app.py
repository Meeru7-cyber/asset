import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import pandas_datareader.data as web
import requests

# 페이지 기본 설정
st.set_page_config(page_title="프라이빗 통합 투자 플랫폼", layout="wide")

# ==========================================
# 🧭 공통 기능: CNN Fear & Greed & 주식 정보 가져오기
# ==========================================
@st.cache_data(ttl=3600)
def get_fear_and_greed():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata", headers=headers, timeout=5)
        data = res.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        return score, rating
    except:
        return None, None

@st.cache_data(ttl=600)
def get_stock_info(ticker):
    """현재가와 예상 주당 배당금을 함께 반환"""
    if not ticker or ticker == "직접 입력": return 0.0, 0.0
    try:
        t = yf.Ticker(ticker)
        # 현재가 추출
        price = float(t.history(period="1d")['Close'].iloc[-1])
        # 배당금 추출 (우선적으로 dividendRate를 찾고, 없으면 trailingAnnualDividendRate 적용)
        info = t.info
        dividend = info.get('dividendRate', info.get('trailingAnnualDividendRate', 0.0))
        if dividend is None: dividend = 0.0
        return price, float(dividend)
    except:
        return 0.0, 0.0

# 종목 검색용 자동완성 딕셔너리
SEARCH_OPTIONS = [
    "직접 입력 (여기에 없는 종목)",
    "삼성전자 (005930.KS)", "SK하이닉스 (000660.KS)", "현대차 (005380.KS)", "기아 (000270.KS)",
    "NAVER (035420.KS)", "카카오 (035720.KS)", "삼성전기 (009150.KS)", "삼성화재 (000810.KS)",
    "삼성물산 (028260.KS)", "삼성SDI (006400.KS)", "LG화학 (051910.KS)", "LG에너지솔루션 (373220.KS)",
    "셀트리온 (068270.KS)", "KB금융 (105560.KS)", "신한지주 (055550.KS)", "하나금융지주 (086790.KS)",
    "에코프로 (086520.KQ)", "에코프로비엠 (247540.KQ)", "두산에너빌리티 (034020.KS)", "POSCO홀딩스 (005490.KS)",
    "KODEX 200 (069500.KS)", "TIGER 미국나스닥100 (133690.KS)", "TIGER 미국S&P500 (360750.KS)",
    "KODEX 미국S&P500TR (379800.KS)", "KODEX 미국채10년선물 (308620.KS)", "ACE KRX금현물 (411060.KS)",
    "KODEX 선진국MSCI World (251350.KS)", "KODEX 단기채권 (153130.KS)", "TIGER 단기통안채 (130680.KS)",
    "Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Tesla (TSLA)", "Alphabet (GOOGL)",
    "SPDR S&P 500 (SPY)", "Invesco QQQ (QQQ)", "iShares 20+ Year Treasury (TLT)", "Schwab US Dividend (SCHD)"
]

# ==========================================
# 🎨 메인 타이틀 및 F&G 배너 (첨부 이미지 스타일 적용)
# ==========================================
st.markdown("<h1 style='text-align: center;'>📊 프라이빗 통합 투자 플랫폼</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b90a8; margin-top: -10px;'>물타기 · 지수분할 · 기대수익률 · 자산배분 통합 계산</p>", unsafe_allow_html=True)

fng_score, fng_rating = get_fear_and_greed()
if fng_score:
    # 점수에 따른 색상 지정
    color_map = {
        "Extreme Fear": ("#e74c3c", "rgba(231,76,60,0.15)"),
        "Fear": ("#e67e22", "rgba(230,126,34,0.15)"),
        "Neutral": ("#f1c40f", "rgba(241,196,15,0.15)"),
        "Greed": ("#2ecc71", "rgba(46,204,113,0.15)"),
        "Extreme Greed": ("#27ae60", "rgba(39,174,96,0.15)")
    }
    text_color, bg_color = color_map.get(fng_rating, ("#f1c40f", "rgba(241,196,15,0.1)"))

    banner_html = f"""
    <div style="background-color: #222536; border: 1px solid #2e3147; border-radius: 12px; padding: 16px 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="font-weight: 700; color: #e8eaf0; font-size: 1.1em; display: flex; align-items: center; gap: 8px;">
            🧭 CNN Fear & Greed Index
        </div>
        <div style="font-size: 1.6em; font-weight: 800; color: #e8eaf0; display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 0.5em; padding: 4px 12px; border-radius: 20px; background: {bg_color}; color: {text_color}; border: 1px solid {text_color}; text-transform: uppercase;">{fng_rating}</span> {fng_score}
        </div>
    </div>
    """
    st.markdown(banner_html, unsafe_allow_html=True)
st.divider()

# ==========================================
# 🧭 사이드바 및 공통 변수
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
    tab_stock, tab_idx, tab_asset, tab_roe = st.tabs([
        "📊 개별종목 물타기", "📉 지수 물타기", "🗂️ 자산배분 리밸런싱", "📈 기대수익률(R)"
    ])
    
    # --- 1. 개별종목 물타기 ---
    with tab_stock:
        st.write("개별종목 분할매수 스케줄 계산 (입력 시 가격 및 배당금 자동완성 지원)")
        
        selected_stock = st.selectbox("🔍 종목 검색 (클릭 후 타이핑하세요)", options=SEARCH_OPTIONS, index=1)
        
        stock_ticker = ""
        if selected_stock == "직접 입력 (여기에 없는 종목)":
            stock_ticker = st.text_input("종목 코드 직접 입력 (예: 005930.KS, AAPL)")
        else:
            stock_ticker = selected_stock.split("(")[-1].replace(")", "").strip()
            
        fetched_price, fetched_div = get_stock_info(stock_ticker) if stock_ticker else (0.0, 0.0)
        
        c1, c2, c3, c4 = st.columns(4)
        budget = c1.number_input("총 투자 금액 (원)", value=15000000, step=1000000)
        start_price = c2.number_input("1회차 매수 가격 (자동입력)", value=float(fetched_price) if fetched_price > 0 else 14000.0, step=100.0)
        dividend_input = c3.number_input("예상 주당 배당금 (자동입력)", value=float(fetched_div), step=10.0)
        steps = c4.number_input("분할 횟수", min_value=2, max_value=20, value=5)
        
        st.divider()
        drop_type = st.radio("하락폭 설정", ["일괄 (매회 동일)", "직접 입력"], horizontal=True)
        
        drops = []
        if drop_type == "일괄 (매회 동일)":
            fixed_drop = st.number_input("회당 하락 금액 (원)", value=1000, step=100)
            drops = [fixed_drop] * (steps - 1)
        else:
            st.write("회차별 하락 금액 설정 (이전 회차 대비)")
            drop_cols = st.columns(steps - 1)
            for i in range(steps - 1):
                val = drop_cols[i].number_input(f"{i+1}➔{i+2}차", value=1000, step=100, key=f"drop_{i}")
                drops.append(val)
                
        if st.button("개별종목 계산하기", type="primary"):
            w_sum = (steps * (steps + 1)) / 2
            res, t_spent, t_shares = [], 0, 0
            curr_price = start_price
            
            for i in range(1, steps + 1):
                target_amt = budget * (i / w_sum)
                if i > 1: curr_price -= drops[i-2]
                if curr_price <= 0: break
                
                shares = round(target_amt / curr_price)
                actual = shares * curr_price
                t_spent += actual
                t_shares += shares
                res.append({"회차": f"{i}차 ({i}배수)", "목표금액": round(target_amt), "매수가격": curr_price, "매수수량": shares, "체결금액": actual})
            
            st.dataframe(pd.DataFrame(res).style.format({"목표금액": "{:,.0f}원", "매수가격": "{:,.0f}원", "체결금액": "{:,.0f}원", "매수수량": "{:,.0f}주"}), use_container_width=True)
            
            avg_price = int(t_spent/t_shares) if t_shares > 0 else 0
            yield_rate = (dividend_input / avg_price) * 100 if avg_price > 0 and dividend_input > 0 else 0.0
            st.success(f"**총 매수금액:** {t_spent:,.0f}원 | **평균단가:** {avg_price:,.0f}원 | **예상 배당률:** {yield_rate:.2f}% | **누적수량:** {t_shares:,.0f}주")

    # --- 2. 지수 물타기 ---
    with tab_idx:
        st.write("지수/ETF 분할매수 스케줄 계산 (입력 시 가격 자동완성 지원)")
        selected_idx = st.selectbox("🔍 지수/ETF 검색", options=SEARCH_OPTIONS, index=21, key="idx_search") 
        
        idx_ticker = ""
        if selected_idx == "직접 입력 (여기에 없는 종목)":
            idx_ticker = st.text_input("ETF 코드 직접 입력", key="idx_custom")
        else:
            idx_ticker = selected_idx.split("(")[-1].replace(")", "").strip()
            
        fetched_idx_price, _ = get_stock_info(idx_ticker) if idx_ticker else (0.0, 0.0)

        i1, i2, i3, i4 = st.columns(4)
        idx_budget = i1.number_input("지수 총 투자 금액", value=15000000, step=1000000)
        idx_start = i2.number_input("첫 매수 지수/단가 (자동입력)", value=float(fetched_idx_price) if fetched_idx_price > 0 else 35000.0, step=100.0)
        idx_drop = i3.number_input("구간별 하락률 (%)", value=5.0, step=0.5)
        idx_steps = i4.number_input("지수 분할 횟수", min_value=2, max_value=20, value=5)
        
        if st.button("지수 계산하기", type="primary"):
            w_sum = (idx_steps * (idx_steps + 1)) / 2
            res_idx, t_spent_idx, t_shares_idx = [], 0, 0
            
            for i in range(1, idx_steps + 1):
                target_amt = idx_budget * (i / w_sum)
                curr_idx = idx_start * (1 - (idx_drop / 100) * (i - 1))
                if curr_idx <= 0: break
                
                shares = round(target_amt / curr_idx)
                actual = shares * curr_idx
                t_spent_idx += actual
                t_shares_idx += shares
                res_idx.append({"회차": f"{i}차 (-{idx_drop*(i-1)}%)", "목표금액": round(target_amt), "매수지수": round(curr_idx, 2), "매수수량": shares, "체결금액": round(actual)})
            
            st.dataframe(pd.DataFrame(res_idx).style.format({"목표금액": "{:,.0f}원", "체결금액": "{:,.0f}원", "매수수량": "{:,.0f}주"}), use_container_width=True)
            st.success(f"**총 매수금액:** {t_spent_idx:,.0f}원 | **평균단가:** {int(t_spent_idx/t_shares_idx) if t_shares_idx > 0 else 0:,.0f}원 | **누적수량:** {t_shares_idx:,.0f}주")

    # --- 3. 자산배분 리밸런싱 ---
    with tab_asset:
        st.write("포트폴리오 비중 조절 (리밸런싱) 계산기")
        total_asset_budget = st.number_input("총 투자 운용 금액 (원)", value=100000000, step=1000000)
        
        if 'asset_df' not in st.session_state:
            st.session_state.asset_df = pd.DataFrame([
                {"자산명 (선택)": "KODEX 200 (069500.KS)", "현재가(원)": 35000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": "TIGER 미국S&P500 (360750.KS)", "현재가(원)": 15000.0, "목표비중(%)": 30.0, "보유수량(주)": 0},
                {"자산명 (선택)": "KODEX 미국채10년선물 (308620.KS)", "현재가(원)": 11000.0, "목표비중(%)": 20.0, "보유수량(주)": 0},
                {"자산명 (선택)": "ACE KRX금현물 (411060.KS)", "현재가(원)": 13000.0, "목표비중(%)": 20.0, "보유수량(주)": 0}
            ])
            
        column_config = {
            "자산명 (선택)": st.column_config.SelectboxColumn("자산명 (클릭하여 검색)", options=SEARCH_OPTIONS[1:], width="large", required=True),
            "현재가(원)": st.column_config.NumberColumn("현재가(원)", format="%d"),
            "목표비중(%)": st.column_config.NumberColumn("목표비중(%)", min_value=0.0, max_value=100.0),
            "보유수량(주)": st.column_config.NumberColumn("보유수량(주)", min_value=0)
        }

        edited_df = st.data_editor(st.session_state.asset_df, num_rows="dynamic", column_config=column_config, use_container_width=True)
        st.session_state.asset_df = edited_df
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            if st.button("🔄 현재가 일괄 업데이트"):
                with st.spinner("현재가를 조회중입니다..."):
                    updated_df = edited_df.copy()
                    for idx, row in updated_df.iterrows():
                        asset_str = row["자산명 (선택)"]
                        if asset_str and "(" in asset_str:
                            ticker = asset_str.split("(")[-1].replace(")", "").strip()
                            price, _ = get_stock_info(ticker)
                            if price > 0:
                                updated_df.at[idx, "현재가(원)"] = price
                    st.session_state.asset_df = updated_df
                    st.rerun()

        total_ratio = edited_df["목표비중(%)"].sum()
        if total_ratio != 100:
            st.error(f"목표 비중의 합이 100%가 아닙니다. (현재: {total_ratio}%)")
        else:
            if st.button("계산하기", type="primary"):
                result_df = edited_df.copy()
                result_df["목표수량(주)"] = np.floor((total_asset_budget * (result_df["목표비중(%)"]/100)) / result_df["현재가(원)"])
                result_df["추가매수(주)"] = result_df["목표수량(주)"] - result_df["보유수량(주)"]
                
                def color_action(val):
                    color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                    return f'color: {color}; font-weight: bold;'
                
                st.dataframe(result_df.style.applymap(color_action, subset=["추가매수(주)"]), use_container_width=True)

    # --- 4. 기대수익률 (ROE/PBR) ---
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
