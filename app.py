import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import plotly.graph_objects as go

# Configuração mobile-first para o iPhone
st.set_page_config(page_title="Radar Institucional", page_icon="📡", layout="centered")

# Força o fuso horário de Brasília para sincronizar com o computador
fuso_br = pytz.timezone('America/Sao_Paulo')

st.markdown("### 📡 Radar Multimercados v13.0")
st.write(f"Última atualização (Brasília): {datetime.now(fuso_br).strftime('%H:%M:%S')}")

# Abas e Perfil Operacional táteis
perfil = st.radio("Selecione o Perfil:", ('Day Trade (5m)', 'Swing Trade (15m)'), horizontal=True)

if 'Day Trade' in perfil:
    tempo_grafico = '5m'
    janela_stop = 12
    periodo_intra = '1d'
else:
    tempo_grafico = '15m'
    janela_stop = 32
    periodo_intra = '5d'

ativos = {
    'Nasdaq 100': 'NQ=F', 'S&P 500': 'ES=F', 'Dow Jones': 'YM=F',
    'Ouro Macro': 'GC=F', 'Prata Metal': 'SI=F', 'Petróleo Brent': 'BZ=F', 
    'NVIDIA': 'NVDA', 'Bitcoin': 'BTC-USD', 'Dólar': 'BRL=X', 
    'Ibovespa': '^BVSP', 'Petrobras': 'PETR4.SA', 'Vale': 'VALE3.SA'
}

# 📋 MAPEAMENTO DA AGENDA MACRO DE ALTO IMPACTO (Horário de Brasília)
NOTICIAS_DO_DIA = [
    {"ID": "ADP Employment Report (Prévia Payroll)", "inicio": "09:12", "fim": "09:20", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "PCE Inflation / Nonfarm Payrolls (Dado Oficial)", "inicio": "09:28", "fim": "09:40", "impacto": "🔥 CRÍTICO"},
    {"ID": "Abertura à Vista NY / ISM Manufacturing PMI", "inicio": "10:28", "fim": "10:42", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "Estoques de Petróleo EIA (Gera Volatilidade Brent)", "inicio": "11:28", "fim": "11:38", "impacto": "🟡 MÉDIO IMPACTO"},
    {"ID": "Janela de Almoço em Wall Street (Falta de Liquidez)", "inicio": "12:28", "fim": "12:45", "impacto": "⏳ RISCO TÉCNICO"}
]

aba_mercado, aba_noticias = st.tabs(["📊 Sinais e Pivô", "📰 Agenda de Travas"])

with aba_noticias:
    st.write("📋 **Grade de Monitoramento de Volatilidade:**")
    for n in NOTICIAS_DO_DIA:
        st.warning(f"🕒 {n['inicio']} até {n['fim']} - **{n['ID']}** [{n['impacto']}]")

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

def checar_trava_noticias():
    agora_str = datetime.now(fuso_br).strftime("%H:%M")
    agora_dt = datetime.strptime(agora_str, "%H:%M")
    for noticia in NOTICIAS_DO_DIA:
        inicio_dt = datetime.strptime(noticia["inicio"], "%H:%M")
        fim_dt = datetime.strptime(noticia["fim"], "%H:%M")
        if inicio_dt <= agora_dt <= fim_dt:
            return True, noticia["ID"], noticia["fim"], noticia["impacto"]
    return False, "", "", ""

with aba_mercado:
    esta_travado, motivo_trava, hora_liberacao, grau_impacto = checar_trava_noticias()
    
    if esta_travado:
        st.warning(f"⚠️ **SINAIS CONGELADOS:** {grau_impacto}\n\n📌 **Motivo:** {motivo_trava}\n\n⏳ **Liberação Operacional às:** {hora_liberacao}")
    else:
        st.success("🛡️ **Varredura Total Liberada:** Sem notícias impactantes travando a grade agora.")

    lista_tabela = []
    dados_grafico = {}
    
    # 🔄 Captura e tratamento simultâneo para a tabela e o gráfico de comparação
    for nome, ticker in ativos.items():
        dados_diarios = yf.download(tickers=ticker, period='3d', interval='1d', progress=False)
        dados_intra = yf.download(tickers=ticker, period=periodo_intra, interval=tempo_grafico, progress=False)
        
        if not dados_diarios.empty and len(dados_diarios) >= 2 and not dados_intra.empty and len(dados_intra) >= 20:
            high_raw = dados_diarios['High'].to_numpy().flatten()
            low_raw = dados_diarios['Low'].to_numpy().flatten()
            close_raw = dados_diarios['Close'].to_numpy().flatten()
            
            maxima_ant = float(high_raw[-2])
            minima_ant = float(low_raw[-2])
            fechamento_ant = float(close_raw[-2])
            
            P = (maxima_ant + minima_ant + fechamento_ant) / 3
            R1 = (2 * P) - minima_ant
            S1 = (2 * P) - maxima_ant
            
            fechamentos_intra = dados_intra['Close'].to_numpy().flatten()
            ultimo_fechamento = float(fechamentos_intra[-1])
            
            # Guarda dados apenas dos índices para montar o gráfico comparativo limpo
            if nome in ['Dow Jones', 'S&P 500', 'Nasdaq 100']:
                # Calcula variação percentual desde o primeiro candle mapeado no dia
                preco_inicial = float(fechamentos_intra[0])
                dados_grafico[nome] = {
                    'tempos': dados_intra.index,
                    'variacoes': ((dados_intra['Close'] - preco_inicial) / preco_inicial) * 100
                }
            
            if len(fechamentos_intra) >= 201:
                ma9 = float(pd.Series(fechamentos_intra).rolling(window=9).mean().iloc[-1])
                ma21 = float(pd.Series(fechamentos_intra).rolling(window=21).mean().iloc[-1])
                ma200 = float(pd.Series(fechamentos_intra).rolling(window=200).mean().iloc[-1])
                ifr = calcular_ifr(dados_intra, 14)
                
                vies_pivo = "🔼 ACIMA" if ultimo_fechamento > P else "🔽 ABAIXO"
                
                if esta_travado:
                    sinal = "🔒 BLOQUEADO"
                else:
                    sinal = "⚪ NEUTRO"
                    if ultimo_fechamento > ma9 and ma9 > ma21 and ultimo_fechamento > ma200 and ifr < 65:
                        sinal = "🟢 COMPRA ATIVA"
                        st.toast(f"🟢 GATILHO COMPRA: {nome} a {ultimo_fechamento:,.2f}", icon="🟢")
                    elif ultimo_fechamento < ma9 and ma9 < ma21 and ultimo_fechamento < ma200 and ifr > 35:
                        sinal = "🔴 VENDA ATIVA"
                        st.toast(f"🔴 GATILHO VENDA: {nome} a {ultimo_fechamento:,.2f}", icon="🔴")
                    elif ifr >= 70:
                        sinal = "⚠️ EXAUSTÃO COMPRA"
                    elif ifr <= 30:
                        sinal = "⚠️ EXAUSTÃO VENDA"
                    
                cifr = "R$" if nome in ['Dólar', 'Ibovespa', 'Petrobras', 'Vale'] else "US$"
                
                lista_tabela.append({
                    "Ativo": nome, "Preço": f"{cifr} {ultimo_fechamento:,.2f}",
                    "Viés Pivô": vies_pivo, "Status / Sinal": sinal, 
                    "Pivô Central (P)": f"{cifr} {P:,.2f}",
                    "Sup (S1)": f"{S1:,.2f}", "Res (R1)": f"{R1:,.2f}"
                })

    # --- DESENHO DO GRÁFICO INSTITUCIONAL INTERATIVO ---
    if dados_grafico:
        st.write("### 📈 Gráfico de Comparação de Preços (%)")
        fig = go.Figure()
        
        cores_linhas = {'Dow Jones': '#2962FF', 'S&P 500': '#FF6D00', 'Nasdaq 100': '#00B0FF'}
        
        for nome_ativo, info in dados_grafico.items():
            fig.add_trace(go.Scatter(
                x=info['tempos'], y=info['variacoes'],
                mode='lines', name=nome_ativo,
                line=dict(color=cores_linhas.get(nome_ativo, '#FFFFFF'), width=2)
            ))
            
        # Linha do Pivô Central / Ponto Zero estática de referência
        fig.add_hline(y=0.0, line_dash="dash", line_color="#888888", annotation_text="Eixo do Pivô", annotation_position="top left")
        
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(ticksuffix="%", gridcolor="#333333"),
            xaxis=dict(gridcolor="#333333"),
            hovermode="x unified",
            height=320,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

    if lista_tabela:
        df_painel = pd.DataFrame(lista_tabela)
        def colorir_colunas(row):
            styles = [''] * len(row)
            status_val = row['Status / Sinal']
            vies_val = row['Viés Pivô']
            
            if "COMPRA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #2e4620; color: white; font-weight: bold;'
            elif "VENDA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #5c1d1d; color: white; font-weight: bold;'
            elif "EXAUSTÃO" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #7d6608; color: #fec107; font-weight: bold;'
            elif "BLOQUEADO" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #4a3e1b; color: #ffeb3b; font-weight: bold;'
                
            if "ACIMA" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #4caf50; font-weight: bold;'
            elif "ABAIXO" in vies_val: styles[df_painel.columns.get_loc('Viés Pivô')] = 'color: #f44336; font-weight: bold;'
            return styles

        st.dataframe(df_painel.style.apply(colorir_colunas, axis=1), use_container_width=True, hide_index=True)
