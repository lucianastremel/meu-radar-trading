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

st.markdown("### 📡 Radar Multimercados v18.5")
st.write(f"Última atualização (Brasília): {datetime.now(fuso_br).strftime('%H:%M:%S')}")

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

NOTICIAS_DO_DIA = [
    {"ID": "ADP Employment Report (Prévia Payroll)", "inicio": "09:12", "fim": "09:20", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "PCE Inflation / Nonfarm Payrolls (Dado Oficial)", "inicio": "09:28", "fim": "09:40", "impacto": "🔥 CRÍTICO"},
    {"ID": "Abertura à Vista NY / ISM Manufacturing PMI", "inicio": "10:28", "fim": "10:42", "impacto": "🔴 ALTO IMPACTO"},
    {"ID": "Estoques de Petróleo EIA (Gera Volatilidade Brent)", "inicio": "11:28", "fim": "11:38", "impacto": "🟡 MÉDIO IMPACTO"},
    {"ID": "Janela de Almoço em Wall Street (Falta de Liquidez)", "inicio": "12:28", "fim": "12:45", "impacto": "⏳ RISCO TÉCNICO"}
]

aba_mercado, aba_noticias = st.tabs(["📊 Sinais e Pivô", "📰 Agenda de Trava"])

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

    lista_tickers = list(ativos.values())
    df_all_intra = yf.download(tickers=lista_tickers, period='8d', interval=tempo_grafico, progress=False)
    df_all_diario = yf.download(tickers=lista_tickers, period='4d', interval='1d', progress=False)
    
    if not df_all_intra.empty:
        df_g_filtro = df_all_intra.copy()
        df_g_filtro['DataStr'] = df_g_filtro.index.strftime('%Y-%m-%d')
        hoje_str = datetime.now(fuso_br).strftime('%Y-%m-%d')
        
        df_g_hoje = df_g_filtro[df_g_filtro['DataStr'] == hoje_str]
        if df_g_hoje.empty:
            ultimas_datas = df_g_filtro['DataStr'].unique()
            df_g_hoje = df_g_filtro[df_g_filtro['DataStr'] == ultimas_datas[-1]]
            
        if not df_g_hoje.empty:
            st.write("### 📈 Gráfico de Comparação de Preços (%)")
            fig = go.Figure()
            
            cores_linhas = {'Nasdaq 100': '#00B0FF', 'S&P 500': '#FF6D00', 'Dow Jones': '#2962FF'}
            map_tickers = {'NQ=F': 'Nasdaq 100', 'ES=F': 'S&P 500', 'YM=F': 'Dow Jones'}
            
            if df_g_hoje.index.tz is not None:
                tempos_formatados = df_g_hoje.index.tz_convert('America/Sao_Paulo').strftime('%H:%M')
            else:
                tempos_formatados = df_g_hoje.index.strftime('%H:%M')
                
            for tk in ['NQ=F', 'ES=F', 'YM=F']:
                if 'Close' in df_g_hoje.columns and tk in df_g_hoje['Close'].columns:
                    serie_preco = df_g_hoje['Close'][tk].dropna()
                    if not serie_preco.empty:
                        preco_ini = float(serie_preco.iloc[0])
                        variacoes = ((serie_preco - preco_ini) / preco_ini) * 100
                        nome_ativo = map_tickers[tk]
                        fig.add_trace(go.Scatter(
                            x=list(tempos_formatados[-len(variacoes):]), y=list(variacoes),
                            mode='lines', name=nome_ativo,
                            line=dict(color=cores_linhas[nome_ativo], width=2.5)
                        ))
            
            fig.add_hline(y=0.0, line_dash="dash", line_color="#888888", annotation_text="Eixo do Pivô", annotation_position="bottom left")
            fig.update_layout(
                margin=dict(l=15, r=15, t=15, b=15),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(ticksuffix="%", gridcolor="#222222", zeroline=False),
                xaxis=dict(gridcolor="#222222", nticks=8),
                hovermode="x unified",
                height=340,
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)

    lista_tabela = []
    
    if not df_all_diario.empty and not df_all_intra.empty:
        for nome, ticker in ativos.items():
            high_raw = df_all_diario['High'][ticker].ffill().bfill().to_numpy() if ('High', ticker) in df_all_diario.columns else df_all_diario['High'].ffill().bfill().to_numpy()
            low_raw = df_all_diario['Low'][ticker].ffill().bfill().to_numpy() if ('Low', ticker) in df_all_diario.columns else df_all_diario['Low'].ffill().bfill().to_numpy()
            close_raw = df_all_diario['Close'][ticker].ffill().bfill().to_numpy() if ('Close', ticker) in df_all_diario.columns else df_all_diario['Close'].ffill().bfill().to_numpy()
                
            if ('Close', ticker) in df_all_intra.columns:
                df_i_ativo = pd.DataFrame(df_all_intra.loc[:, (slice(None), ticker)])
                df_i_ativo.columns = df_i_ativo.columns.droplevel(1)
            else:
                df_i_ativo = df_all_intra
            
            df_i_ativo = df_i_ativo.dropna(subset=['Close'])
            fechamentos_intra = df_i_ativo['Close'].to_numpy()
            
            if len(high_raw) >= 2 and len(fechamentos_intra) >= 15:
                maxima_ant = float(high_raw[-2])
                minima_ant = float(low_raw[-2])
                fechamento_ant = float(close_raw[-2])
                
                P = (maxima_ant + minima_ant + fechamento_ant) / 3
                R1 = (2 * P) - minima_ant
                S1 = (2 * P) - maxima_ant
                
                ultimo_fechamento = float(fechamentos_intra[-1])
                vies_pivo = "🔼 ACIMA" if ultimo_fechamento > P else "🔽 ABAIXO"
                
                sinal = "⚪ NEUTRO"
                # Ajuste Técnico Crucial: Reduzido de 201 para 100 para liberar as médias na sessão atual da tarde
                if len(fechamentos_intra) >= 100:
                    ma9 = float(pd.Series(fechamentos_intra).rolling(window=9).mean().iloc[-1])
                    ma21 = float(pd.Series(fechamentos_intra).rolling(window=21).mean().iloc[-1])
                    ifr = calcular_ifr(df_i_ativo, 14)
                    
                    if esta_travado:
                        sinal = "🔒 BLOQUEADO"
                    else:
                        if ultimo_fechamento > ma9 and ma9 > ma21 and ifr < 65:
                            sinal = "🟢 COMPRA ATIVA"
                        elif ultimo_fechamento < ma9 and ma9 < ma21 and ifr > 35:
                            sinal = "🔴 VENDA ATIVA"
                        elif ifr >= 70:
                            sinal = "⚠️ EXAUSTÃO COMPRA"
                        elif ifr <= 30:
                            sinal = "⚠️ EXAUSTÃO VENDA"
                
                cifr = "R$" if nome in ['Dólar', 'Ibovespa', 'Petrobras', 'Vale'] else "US$"
                
                lista_tabela.append({
                    "Ativo": str(nome),
                    "Preço": f"{cifr} {ultimo_fechamento:,.2f}",
                    "Viés Pivô": str(vies_pivo),
                    "Status / Sinal": str(sinal),
                    "Pivô Central (P)": f"{cifr} {P:,.2f}",
                    "Sup (S1)": f"{S1:,.2f}",
                    "Res (R1)": f"{R1:,.2f}"
                })

    if lista_tabela:
        df_painel = pd.DataFrame(lista_tabela)
        def colorir_colunas(row):
            styles = [''] * len(row)
            status_val = row['Status / Sinal']
            vies_val = row['Viés Pivô']
            
            if "COMPRA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #2e4620; color: white; font-weight: bold;'
            elif "VENDA ATIVA" in status_val: styles[df_painel.columns.get_loc('Status / Sinal')] = 'background-color: #5c1d1d; color: white; font-weight: bold;'
