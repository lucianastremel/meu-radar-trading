import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")
fuso_br = pytz.timezone('America/Sao_Paulo')

st.markdown("### 📡 Radar Multimercados v26.5")
st.write(f"Última atualização (Brasília): {datetime.now(fuso_br).strftime('%H:%M:%S')}")

st.info("🎯 Configuração Otimizada para Monitoramento de Pullbacks (15 minutos)")
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
        
    lista_tabela = []
    lista_tickers = list(ativos.values())
    
    # ⚡ Downloads em bloco otimizados de alta velocidade
    df_all_intra = yf.download(tickers=lista_tickers, period='6d', interval=tempo_grafico, progress=False)
    df_all_diario = yf.download(tickers=lista_tickers, period='4d', interval='1d', progress=False)
    
    if not df_all_intra.empty and not df_all_diario.empty:
        for nome, ticker in ativos.items():
            try:
                if 'Close' in df_all_intra.columns and ticker in df_all_intra['Close'].columns:
                    serie_intra = df_all_intra['Close'][ticker].dropna()
                    fechamentos_intra = serie_intra.to_numpy().flatten()
                else: continue
                    
                if 'High' in df_all_diario.columns and ticker in df_all_diario['High'].columns:
                    high_raw = df_all_diario['High'][ticker].dropna().to_numpy().flatten()
                    low_raw = df_all_diario['Low'][ticker].dropna().to_numpy().flatten()
                    close_raw = df_all_diario['Close'][ticker].dropna().to_numpy().flatten()
                else: continue
                
                if len(high_raw) >= 2 and len(fechamentos_intra) >= 5:
                    maxima_ant = float(high_raw[-2])
                    minima_ant = float(low_raw[-2])
                    fechamento_ant = float(close_raw[-2])
                    
                    P = (maxima_ant + minima_ant + fechamento_ant) / 3
                    S1 = (2 * P) - maxima_ant
                    R1 = (2 * P) - minima_ant
                    
                    ultimo_fechamento = float(fechamentos_intra[-1])
                    sinal = "⚪ NEUTRO"
                    
                    if len(fechamentos_intra) >= 15:
                        ma9 = float(serie_intra.rolling(window=9).mean().iloc[-1])
                        ma21 = float(serie_intra.rolling(window=21).mean().iloc[-1])
                        ifr = calcular_ifr(serie_intra, 14)
                        afastamento = ((ultimo_fechamento - ma9) / ma9) * 100
                        
                        if esta_travado:
                            sinal = "🔒 BLOQUEADO"
                        else:
                            if ifr >= 70 and afastamento >= 0.35:
                                sinal = "⚠️ PULLBACK QUEDA"
                                st.toast(f"⚠️ EXAUSTÃO INSTITUCIONAL: Pullback iminente em {nome}!", icon="⚠️")
                            elif ifr <= 30 and afastamento <= -0.35:
                                sinal = "⚠️ PULLBACK ALTA"
                                st.toast(f"⚠️ EXAUSTÃO INSTITUCIONAL: Pullback iminente em {nome}!", icon="⚠️")
                            elif ultimo_fechamento > ma9 and ma9 > ma21 and ifr < 65:
                                sinal = "🟢 COMPRA ATIVA"
                            elif ultimo_fechamento < ma9 and ma9 < ma21 and ifr > 35:
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
            elif "BLOQUEADO" in status_val: styles[df_painel.columns.get_loc('Status')] = 'background-color: #4a3e1b; color: #ffeb3b; font-weight: bold;'
            if "ACIMA" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #4caf50; font-weight: bold;'
            elif "ABAIXO" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #f44336; font-weight: bold;'
            return styles
        st.dataframe(df_painel.style.apply(colorir_colunas, axis=1), use_container_width=True, hide_index=True)
