import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuração da página para iPhone (Mobile-First)
st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")

st.title("📡 Radar Multimercados v9.0")
st.write(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")

# Chave tátil para mudar o tempo operacional com um toque no celular
perfil = st.radio("Selecione o Perfil:", ('Day Trade (5m)', 'Swing Trade (15m)'), horizontal=True)

if 'Day Trade' in perfil:
    tempo_grafico = '5m'
    janela_stop = 12
else:
    tempo_grafico = '15m'
    janela_stop = 32

# Grade de ativos completa solicitada
ativos = {
    'Nasdaq 100': 'NQ=F', 'S&P 500': 'ES=F', 'Dow Jones': 'YM=F',
    'Ouro Macro': 'GC=F', 'Prata Metal': 'SI=F', 'Petróleo Brent': 'BZ=F', 
    'NVIDIA': 'NVDA', 'Bitcoin': 'BTC-USD', 'Dólar': 'BRL=X', 
    'Ibovespa': '^BVSP', 'Petrobras': 'PETR4.SA', 'Vale': 'VALE3.SA'
}

aba_mercado, aba_noticias = st.tabs(["📊 Sinais e Exaustão", "📰 Agenda Macro"])

with aba_noticias:
    st.info("📌 [ALTO IMPACTO] PCE Inflation e Spending - Quarta-feira")
    st.info("📌 [ALTO IMPACTO] Relatório Nonfarm Payrolls (NFP) - Sexta-feira")
    st.warning("📌 [MÉDIO IMPACTO] JOLTS Job Openings - Terça-feira")

def calcular_ifr(df, periods=14):
    fechamentos = df['Close'].to_numpy().flatten()
    if len(fechamentos) < periods: return 50.0
    deltas = np.diff(fechamentos)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).ewm(com=periods-1, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(losses).ewm(com=periods-1, adjust=False).mean().iloc[-1]
    if avg_loss == 0: return 100.0
    return float(100 - (100 / (1 + (avg_gain / avg_loss))))

with aba_mercado:
    lista_tabela = []
    for nome, ticker in ativos.items():
        dados = yf.download(tickers=ticker, period='6d', interval=tempo_grafico, progress=False)
        
        if not dados.empty and len(dados) >= 201:
            fechamentos = dados['Close'].to_numpy().flatten()
            maximas = dados['High'].to_numpy().flatten()
            minimas = dados['Low'].to_numpy().flatten()
            
            ultimo_fechamento = float(fechamentos[-1])
            ma9 = float(pd.Series(fechamentos).rolling(window=9).mean().iloc[-1])
            ma21 = float(pd.Series(fechamentos).rolling(window=21).mean().iloc[-1])
            ma200 = float(pd.Series(fechamentos).rolling(window=200).mean().iloc[-1])
            ifr = calcular_ifr(dados, 14)
            
            folga_tecnica = ultimo_fechamento * 0.0015
            stop_venda_tecnico = float(np.max(maximas[-janela_stop:]))
            stop_compra_tecnico = float(np.min(minimas[-janela_stop:]))
            
            if stop_venda_tecnico <= ultimo_fechamento: stop_venda_tecnico = ultimo_fechamento + folga_tecnica
            if stop_compra_tecnico >= ultimo_fechamento: stop_compra_tecnico = ultimo_fechamento - folga_tecnica
            
            sinal = "⚪ NEUTRO"
            stop_exibido = "-"
            
            if ultimo_fechamento > ma9 and ma9 > ma21 and ultimo_fechamento > ma200 and ifr < 65:
                sinal = "🟢 COMPRA ATIVA"
                stop_exibido = f"{stop_compra_tecnico:,.2f}"
            elif ultimo_fechamento < ma9 and ma9 < ma21 and ultimo_fechamento < ma200 and ifr > 35:
                sinal = "🔴 VENDA ATIVA"
                stop_exibido = f"{stop_venda_tecnico:,.2f}"
            elif ifr >= 70:
                sinal = "⚠️ EXAUSTÃO COMPRA"
            elif ifr <= 30:
                sinal = "⚠️ EXAUSTÃO VENDA"
                
            cifr = "R$" if nome in ['Dólar', 'Ibovespa', 'Petrobras', 'Vale'] else "US$"
            lista_tabela.append({
                "Ativo": nome, "Preço": f"{cifr} {ultimo_fechamento:,.2f}",
                "IFR": f"{ifr:.1f}", "Status": sinal, "Stop": f"{cifr} {stop_exibido}" if stop_exibido != "-" else "-"
            })
            
    df_painel = pd.DataFrame(lista_tabela)
    def colorir_sinal(val):
        if "COMPRA ATIVA" in val: return 'background-color: #2e4620; color: white; font-weight: bold;'
        if "VENDA ATIVA" in val: return 'background-color: #5c1d1d; color: white; font-weight: bold;'
        if "EXAUSTÃO" in val: return 'background-color: #7d6608; color: #fec107; font-weight: bold;'
        return 'color: gray;'
    st.dataframe(df_painel.style.applymap(colorir_sinal, subset=['Status']), use_container_width=True, hide_index=True)
