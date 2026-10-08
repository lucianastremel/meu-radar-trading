import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")
fuso_br = pytz.timezone('America/Sao_Paulo')

st.markdown("### 📡 Radar Multimercados v28.2")
st.write(f"Última atualização (Brasília): {datetime.now(fuso_br).strftime('%H:%M:%S')}")

st.info("🛡️ Configuração Avançada v28.2: Limpeza de Cache de API + Trava de Fluxo Cruzado")
tempo_grafico = '15m'

ativos = {
    'Nasdaq 100': 'NQ=F', 'S&P 500': 'ES=F', 'Dow Jones': 'YM=F',
    'Ouro Macro': 'GC=F', 'Prata Metal': 'SI=F', 'Petróleo Brent': 'BZ=F', 
    'NVIDIA': 'NVDA', 'Bitcoin': 'BTC-USD', 'Dólar': 'BRL=X', 
    'Ibovespa': '^BVSP', 'Petrobras': 'PETR4.SA', 'Vale': 'VALE3.SA'
}

NOTICIAS_DO_DIA = [
    {"ID": "ADP Employment Report (Prévia Payroll)", "inicio": "09:12", "fim": "09:20", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "PCE Inflation / Nonfarm Payrolls (Dado Oficial)", "inicio": "09:28", "fim": "09:40", "impacto": "🔥 CRÍTICO"},
    {"ID": "Abertura à Vista NY / ISM Manufacturing PMI", "inicio": "10:28", "fim": "10:42", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "Estoques de Petróleo EIA (Gera Volatilidade Brent)", "inicio": "11:28", "fim": "11:38", "impacto": "🟡 MÉDIO IMPACTO"},
    {"ID": "Janela de Almoço em Wall Street (Falta de Liquidez)", "inicio": "12:28", "fim": "12:45", "impacto": "⏳ RISCO TÉCNICO"}
]

aba_mercado, aba_noticias = st.tabs(["📊 Sinais e Pivô", "📰 Agenda Macro"])

with aba_noticias:
    for n in NOTICIAS_DO_DIA:
        st.warning(f"🕒 {n['inicio']} até {n['fim']} - **{n['ID']}**")

def calcular_ifr(df_close, periods=14):
    fechamentos = df_close.to_numpy().flatten()
    if len(fechamentos) < periods: return 50.0
    deltas = np.diff(fechamentos)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).ewm(com=periods-1, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(losses).ewm(com=periods-1, adjust=False).mean().iloc[-1]
    if avg_loss == 0: return 100.0
    return float(100 - (100 / (1 + (avg_gain / avg_loss))))

def checar_trava_noticias():
    agora_str = datetime.now(fuso_br).strftime("%H:%M")
    agora_dt = datetime.strptime(agora_str, "%H:%M")
    for noticia in NOTICIAS_DO_DIA:
        inicio_dt = datetime.strptime(noticia["inicio"], "%H:%M")
        fim_dt = datetime.strptime(noticia["fim"], "%H:%M")
        if inicio_dt <= agora_dt <= fim_dt:
            return True, noticia["ID"], noticia["fim"]
    return False, "", ""

with aba_mercado:
    esta_travado, motivo_trava, hora_liberacao = checar_trava_noticias()
    if esta_travado:
        st.warning(f"🔒 **SINAIS BLOQUEADOS OPERACIONALMENTE:** {motivo_trava} (Liberação às {hora_liberacao})")
        
    lista_tickers = list(ativos.values())
    
    # ⚡ FORÇA O YAHOO FINANCE A LIMPAR O CACHE OPERACIONAL DA SESSÃO TÉCNICA
    df_all_intra = yf.download(tickers=lista_tickers, period='6d', interval=tempo_grafico, progress=False, group_by='ticker', auto_adjust=True)
    df_all_diario = yf.download(tickers=lista_tickers, period='4d', interval='1d', progress=False, group_by='ticker', auto_adjust=True)
    
    nvidia_barrada = False
    bitcoin_abaixo_pivo = False
    
    # Extração robusta limpando estruturas hierárquicas vazias
    try:
        nvda_intra = df_all_intra['NVDA'].dropna(subset=['Close']) if 'NVDA' in df_all_intra.columns.levels[0] else pd.DataFrame()
        nvda_diario = df_all_diario['NVDA'].dropna(subset=['High']) if 'NVDA' in df_all_diario.columns.levels[0] else pd.DataFrame()
        if not nvda_intra.empty and not nvda_diario.empty and len(nvda_diario) >= 2:
            nvda_close = float(nvda_intra['Close'].iloc[-1])
            nvda_p = (float(nvda_diario['High'].iloc[-2]) + float(nvda_diario['Low'].iloc[-2]) + float(nvda_diario['Close'].iloc[-2])) / 3
            nvda_s1 = (2 * nvda_p) - float(nvda_diario['High'].iloc[-2])
            if nvda_close <= (nvda_s1 * 1.0005): nvidia_barrada = True

        btc_intra = df_all_intra['BTC-USD'].dropna(subset=['Close']) if 'BTC-USD' in df_all_intra.columns.levels[0] else pd.DataFrame()
        btc_diario = df_all_diario['BTC-USD'].dropna(subset=['High']) if 'BTC-USD' in df_all_diario.columns.levels[0] else pd.DataFrame()
        if not btc_intra.empty and not btc_diario.empty and len(btc_diario) >= 2:
            btc_close = float(btc_intra['Close'].iloc[-1])
            btc_p = (float(btc_diario['High'].iloc[-2]) + float(btc_diario['Low'].iloc[-2]) + float(btc_diario['Close'].iloc[-2])) / 3
            if btc_close < btc_p: bitcoin_abaixo_pivo = True
    except Exception: pass

    lista_tabela = []
    for nome, ticker in ativos.items():
        try:
            if ticker in df_all_intra.columns.levels[0] and ticker in df_all_diario.columns.levels[0]:
                df_i = df_all_intra[ticker].dropna(subset=['Close'])
                df_d = df_all_diario[ticker].dropna(subset=['High', 'Low', 'Close'])
            else: continue
            
            fechamentos_intra = df_i['Close'].to_numpy().flatten()
            high_raw = df_d['High'].to_numpy().flatten()
            low_raw = df_d['Low'].to_numpy().flatten()
            close_raw = df_d['Close'].to_numpy().flatten()
            
            if len(high_raw) >= 2 and len(fechamentos_intra) >= 5:
                P = (float(high_raw[-2]) + float(low_raw[-2]) + float(close_raw[-2])) / 3
                S1 = (2 * P) - float(high_raw[-2])
                R1 = (2 * P) - float(low_raw[-2])
                
                ultimo_fechamento = float(fechamentos_intra[-1])
                sinal = "⚪ NEUTRO"
                
                if len(fechamentos_intra) >= 15:
                    ma9 = float(df_i['Close'].rolling(window=9).mean().iloc[-1])
                    ma21 = float(df_i['Close'].rolling(window=21).mean().iloc[-1])
                    ifr = calcular_ifr(df_i['Close'], 14)
                    afastamento = ((ultimo_fechamento - ma9) / ma9) * 100
                    
                    if esta_travado:
                        sinal = "🔒 BLOQUEADO"
                    elif 47.0 <= ifr <= 53.0:
                        sinal = "⏳ COMPRESSÃO LATERAL"
                    else:
                        if ifr >= 70 and afastamento >= 0.35:
                            sinal = "⚠️ PULLBACK QUEDA"
                        elif ifr <= 30 and afastamento <= -0.35:
                            sinal = "⚠️ PULLBACK ALTA"
                        elif ultimo_fechamento > ma9 and ma9 > ma21 and ifr < 65:
                            if nome in ['Nasdaq 100', 'S&P 500', 'Dow Jones'] and (nvidia_barrada or bitcoin_abaixo_pivo):
                                sinal = "⏳ BARRADO (Divergência NVDA/BTC)"
                            elif ultimo_fechamento >= (R1 * 0.9995):
                                sinal = "⏳ BARRADO (Alvo R1)"
                            else:
                                sinal = "🟢 COMPRA ATIVA"
                        elif ultimo_fechamento < ma9 and ma9 < ma21 and ifr > 35:
                            if ultimo_fechamento <= (S1 * 1.0005):
                                sinal = "⏳ BARRADO (Alvo S1)"
                            else:
                                sinal = "🔴 VENDA ATIVA"
                
                vies_pivo = "🔼 ACIMA" if ultimo_fechamento > P else "🔽 ABAIXO"
                cifr = "R$" if nome in ['Dólar', 'Ibovespa', 'Petrobras', 'Vale'] else "US$"
                
                lista_tabela.append({
                    "Ativo": nome, "Preço": f"{cifr} {ultimo_fechamento:,.2f}",
                    "Viés Pivô": vies_pivo, "Status": sinal, 
                    "Pivô Central (P)": f"{cifr} {P:,.2f}", "Sup (S1)": f"{S1:,.2f}", "Res (R1)": f"{R1:,.2f}"
                })
        except Exception: continue
        
    if lista_tabela:
        df_painel = pd.DataFrame(lista_tabela)
        def colorir_colunas(row):
            styles = [''] * len(row)
            status_val = row['Status']
            vies_val = row['Viés Pivô']
            if "COMPRA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #2e4620; color: white; font-weight: bold;'
            elif "VENDA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #5c1d1d; color: white; font-weight: bold;'
            elif "PULLBACK" in status_val or "⚠️" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #7d6608; color: #fec107; font-weight: bold;'
            elif "BARRADO" in status_val or "COMPRESSÃO" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #2c3e50; color: #b2bec3; font-weight: bold;'
            elif "BLOQUEADO" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #4a3e1b; color: #ffeb3b; font-weight: bold;'
            if "ACIMA" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #4caf50; font-weight: bold;'
            elif "ABAIXO" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #f44336; font-weight: bold;'
            return styles
        st.dataframe(df_painel.style.apply(colorir_colunas, axis=1), use_container_width=True, hide_index=True)
