import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuração da página para iPhone (Mobile-First)
st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")

st.title("📡 Radar Multimercados v10.0")
st.write(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")

# Chave tátil para mudar o tempo operacional com um toque no celular
perfil = st.radio("Selecione o Perfil:", ('Day Trade (5m)', 'Swing Trade (15m)'), horizontal=True)

if 'Day Trade' in perfil:
    tempo_grafico = '5m'
    janela_stop = 12
else:
    tempo_grafico = '15m'
    janela_stop = 32

# Grade de ativos completa
ativos = {
    'Nasdaq 100': 'NQ=F', 'S&P 500': 'ES=F', 'Dow Jones': 'YM=F',
    'Ouro Macro': 'GC=F', 'Prata Metal': 'SI=F', 'Petróleo Brent': 'BZ=F', 
    'NVIDIA': 'NVDA', 'Bitcoin': 'BTC-USD', 'Dólar': 'BRL=X', 
    'Ibovespa': '^BVSP', 'Petrobras': 'PETR4.SA', 'Vale': 'VALE3.SA'
}

aba_mercado, aba_noticias = st.tabs(["📊 Sinais e Pivô", "📰 Agenda Macro"])

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
        # 1. Puxa dados diários para calcular o Pivô do dia anterior
        dados_diarios = yf.download(tickers=ticker, period='2d', interval='1d', progress=False)
        
        # 2. Puxa dados intradiários para as Médias e IFR
        dados_intra = yf.download(tickers=ticker, period='6d', interval=tempo_grafico, progress=False)
        
        if not dados_diarios.empty and len(dados_diarios) >= 2 and not dados_intra.empty and len(dados_intra) >= 201:
            # Dados do dia anterior (índice -2 na tabela diária)
            maxima_ant = float(dados_diarios['High'].iloc[-2])
            minima_ant = float(dados_diarios['Low'].iloc[-2])
            fechamento_ant = float(dados_diarios['Close'].iloc[-2])
            
            # --- CÁLCULO MATEMÁTICO DOS PONTOS DE PIVÔ ---
            P = (maxima_ant + minima_ant + fechamento_ant) / 3
            R1 = (2 * P) - minima_ant
            S1 = (2 * P) - maxima_ant
            R2 = P + (maxima_ant - minima_ant)
            S2 = P - (maxima_ant - minima_ant)
            R3 = maxima_ant + 2 * (P - minima_ant)
            S3 = minima_ant - 2 * (maxima_ant - P)
            
            # Dados intraday atuais
            fechamentos = dados_intra['Close'].to_numpy().flatten()
            maximas = dados_intra['High'].to_numpy().flatten()
            minimas = dados_intra['Low'].to_numpy().flatten()
            
            ultimo_fechamento = float(fechamentos[-1])
            ma9 = float(pd.Series(fechamentos).rolling(window=9).mean().iloc[-1])
            ma21 = float(pd.Series(fechamentos).rolling(window=21).mean().iloc[-1])
            ma200 = float(pd.Series(fechamentos).rolling(window=200).mean().iloc[-1])
            ifr = calcular_ifr(dados_intra, 14)
            
            folga_tecnica = ultimo_fechamento * 0.0015
            stop_venda_tecnico = float(np.max(maximas[-janela_stop:]))
            stop_compra_tecnico = float(np.min(minimas[-janela_stop:]))
            
            if stop_venda_tecnico <= ultimo_fechamento: stop_venda_tecnico = ultimo_fechamento + folga_tecnica
            if stop_compra_tecnico >= ultimo_fechamento: stop_compra_tecnico = ultimo_fechamento - folga_tecnica
            
            # --- VIÉS DO PIVÔ CENTRAL ---
            vies_pivo = "🔼 ACIMA DO PIVÔ" if ultimo_fechamento > P else "🔽 ABAIXO DO PIVÔ"
            
            # --- MOTOR DE INTELIGÊNCIA ---
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
                "Ativo": nome, 
                "Preço": f"{cifr} {ultimo_fechamento:,.2f}",
                "Viés Pivô": vies_pivo,
                "Status": sinal, 
                "Pivô Central (P)": f"{cifr} {P:,.2f}",
                "Sup (S1 / S2)": f"{S1:,.2f} / {S2:,.2f}",
                "Res (R1 / R2)": f"{R1:,.2f} / {R2:,.2f}"
            })
            
    if lista_tabela:
        df_painel = pd.DataFrame(lista_tabela)
        def colorir_sinal(val):
            if "COMPRA ATIVA" in val: return 'background-color: #2e4620; color: white; font-weight: bold;'
            if "VENDA ATIVA" in val: return 'background-color: #5c1d1d; color: white; font-weight: bold;'
            if "EXAUSTÃO" in val: return 'background-color: #7d6608; color: #fec107; font-weight: bold;'
            return 'color: gray;'
            
        def colorir_vies(val):
            if "ACIMA" in val: return 'color: #4caf50; font-weight: bold;'
            if "ABAIXO" in val: return 'color: #f44336; font-weight: bold;'
            return ''

        st.dataframe(
            df_painel.style.map(colorir_sinal, subset=['Status']).map(colorir_vies, subset=['Viés Pivô']), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.warning("Aguardando o carregamento dos dados dos ativos...")
