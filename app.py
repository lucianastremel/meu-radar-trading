import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuração mobile-first para o iPhone
st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")

st.markdown("### 📡 Radar Multimercados v10.0")
st.write(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")

# Abas e Perfil Operacional táteis
perfil = st.radio("Selecione o Perfil:", ('Day Trade (5m)', 'Swing Trade (15m)'), horizontal=True)

if 'Day Trade' in perfil:
    tempo_grafico = '5m'
    janela_stop = 12
else:
    tempo_grafico = '15m'
    janela_stop = 32

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
        dados_diarios = yf.download(tickers=ticker, period='2d', interval='1d', progress=False)
        dados_intra = yf.download(tickers=ticker, period='6d', interval=tempo_grafico, progress=False)
        
        if not dados_diarios.empty and len(dados_diarios) >= 2 and not dados_intra.empty and len(dados_intra) >= 201:
            maxima_ant = float(dados_diarios['High'].iloc[-2])
            minima_ant = float(dados_diarios['Low'].iloc[-2])
            fechamento_ant = float(dados_diarios['Close'].iloc[-2])
            
            # Cálculo Matemático Clássico dos Pontos de Pivô
            P = (maxima_ant + minima_ant + fechamento_ant) / 3
            R1 = (2 * P) - minima_ant
            S1 = (2 * P) - maxima_ant
            R2 = P + (maxima_ant - minima_ant)
            S2 = P - (maxima_ant - minima_ant)
            
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
            
            vies_pivo = "🔼 ACIMA" if ultimo_fechamento > P else "🔽 ABAIXO"
            
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
                "Sup (S1/S2)": f"{S1:,.2f} / {S2:,.2f}",
                "Res (R1/R2)": f"{R1:,.2f} / {R2:,.2f}"
            })
            
    if lista_tabela:
        df_painel = pd.DataFrame(lista_tabela)
        
        def colorir_colunas(row):
            styles = [''] * len(row)
            status_val = row['Status']
            vies_val = row['Viés Pivô']
            
            if "COMPRA ATIVA" in status_val:
                styles[df_painel.columns.get_loc('Status')] = 'background-color: #2e4620; color: white; font-weight: bold;'
            elif "VENDA ATIVA" in status_val:
                styles[df_painel.columns.get_loc('Status')] = 'background-color: #5c1d1d; color: white; font-weight: bold;'
            elif "EXAUSTÃO" in status_val:
                styles[df_painel.columns.get_loc('Status')] = 'background-color: #7d6608; color: #fec107; font-weight: bold;'
                
            if "ACIMA" in vies_val:
                styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #4caf50; font-weight: bold;'
            elif "ABAIXO" in vies_val:
                styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #f44336; font-weight: bold;'
                
            return styles

        st.dataframe(df_painel.style.apply(colorir_colunas, axis=1), use_container_width=True, hide_index=True)
    else:
        st.warning("Aguardando carregamento de dados...")
