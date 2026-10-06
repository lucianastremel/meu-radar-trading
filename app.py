import yfinance as yf
import pandas as pd
import numpy as np
import time
import os
import shutil
from datetime import datetime
import pytz
from winotify import Notification, audio
from colorama import init, Fore, Style

init(autoreset=True)

PERFIL_OPERACIONAL = 'SWING_TRADE'  # Gráfico de 15 minutos recomendado
TEMPO_GRAFICO = '15m'
JANELA_STOP = 32       
SEGUNDOS_ESPERA = 300  # Varredura a cada 5 minutos

fuso_br = pytz.timezone('America/Sao_Paulo')

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

CAMINHO_DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
ARQUIVO_LOG = os.path.join(CAMINHO_DESKTOP, "historico_sinais.txt")
DIA_ATUAL_LOG = datetime.now(fuso_br).strftime('%Y-%m-%d')

def gerenciar_tamanho_log():
    global DIA_ATUAL_LOG
    dia_hoje = datetime.now(fuso_br).strftime('%Y-%m-%d')
    if dia_hoje != DIA_ATUAL_LOG:
        if os.path.exists(ARQUIVO_LOG):
            arquivo_backup = os.path.join(CAMINHO_DESKTOP, f"historico_sinais_{DIA_ATUAL_LOG}.txt")
            try: shutil.move(ARQUIVO_LOG, arquivo_backup)
            except Exception: pass
        DIA_ATUAL_LOG = dia_hoje

def disparar_notificacao_windows(ativo, tipo_sinal, preco, detalhe=""):
    toast = Notification(
        app_id="Ranger Radar Trading",
        title=f"📡 ALERTA: {tipo_sinal}",
        msg=f"Ativo: {ativo}\nPreço: {preco}\n{detalhe}",
        duration="long"
    )
    toast.set_audio(audio.Reminder, loop=False)
    toast.show()

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
            return True, noticia["ID"], noticia["fim"], noticia["impacto"]
    return False, "", "", ""

def verificar_mercado():
    esta_travado, motivo_trava, hora_liberacao, grau_impacto = checar_trava_noticias()
    
    print(Fore.CYAN + "============================================================")
    print(Fore.CYAN + "   📡 MATRIZ INSTITUCIONAL v27.0 - SUPER ASSERTIVO 15M      ")
    print(Fore.CYAN + "============================================================")
    print(f"Relógio Sistema: {datetime.now(fuso_br).strftime('%H:%M:%S')}")
    print("-" * 60)
    
    if esta_travado:
        print(Fore.YELLOW + f"❌ SINAIS CONGELADOS: {motivo_trava} | Liberação: {hora_liberacao}")
        print("-" * 60)

    lista_tickers = list(ativos.values())
    df_all_intra = yf.download(tickers=lista_tickers, period='6d', interval=TEMPO_GRAFICO, progress=False)
    df_all_diario = yf.download(tickers=lista_tickers, period='4d', interval='1d', progress=False)
    
    for nome, ticker in ativos.items():
        try:
            if not df_all_intra.empty and 'Close' in df_all_intra.columns and ticker in df_all_intra['Close'].columns:
                serie_intra = df_all_intra['Close'][ticker].dropna()
                fechamentos = serie_intra.to_numpy().flatten()
            else: continue
                
            if not df_all_diario.empty and 'High' in df_all_diario.columns and ticker in df_all_diario['High'].columns:
                high_raw = df_all_diario['High'][ticker].dropna().to_numpy().flatten()
                low_raw = df_all_diario['Low'][ticker].dropna().to_numpy().flatten()
                close_raw = df_all_diario['Close'][ticker].dropna().to_numpy().flatten()
            else: continue
                
            if len(fechamentos) < 22 or len(high_raw) < 2: continue
                
            # Cálculo dos pontos de Pivô Diário para filtragem técnica
            maxima_ant = float(high_raw[-2])
            minima_ant = float(low_raw[-2])
            fechamento_ant = float(close_raw[-2])
            P = (maxima_ant + minima_ant + fechamento_ant) / 3
            S1 = (2 * P) - maxima_ant
            R1 = (2 * P) - minima_ant
            
            ultimo_fechamento = float(fechamentos[-1])
            ma9 = float(serie_intra.rolling(window=9).mean().iloc[-1])
            ma21 = float(serie_intra.rolling(window=21).mean().iloc[-1])
            ifr = calcular_ifr(serie_intra, 14)
            afastamento = ((ultimo_fechamento - ma9) / ma9) * 100
            cifr = "R$" if nome in ['Dólar', 'Ibovespa', 'Petrobras', 'Vale'] else "US$"
            
            # 🚨 1. FILTRO DE SEGURANÇA: COMPRESSÃO LATERAL (ZONA MORTA DO IFR)
            if 47.0 <= ifr <= 53.0:
                print(f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | " + Fore.LIGHTBLACK_EX + "⏳ NEUTRO (Filtro Lateral Consolidado)")
                continue

            # 🎯 DETECÇÃO DE PULLBACK
            if ifr >= 70 and afastamento >= 0.35:
                print(Fore.YELLOW + Style.BRIGHT + f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | ⚠️ PULLBACK QUEDA IMINENTE")
                if not esta_travado: disparar_notificacao_windows(nome, "PULLBACK QUEDA IMINENTE", f"IFR: {ifr:.1f}")
            elif ifr <= 30 and afastamento <= -0.35:
                print(Fore.YELLOW + Style.BRIGHT + f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | ⚠️ PULLBACK ALTA IMINENTE")
                if not esta_travado: disparar_notificacao_windows(nome, "PULLBACK ALTA IMINENTE", f"IFR: {ifr:.1f}")
            
            # TENDÊNCIA PADRÃO COM FILTROS DE PIVÔ DIÁRIO
            elif ultimo_fechamento > ma9 and ma9 > ma21 and ifr < 65:
                # 🚨 2. FILTRO DE SEGURANÇA: BARREIRA DA RESISTÊNCIA R1
                if ultimo_fechamento >= (R1 * 0.9995):
                    print(f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | " + Fore.LIGHTBLACK_EX + "⏳ COMPRA BARRADA (Preço colado no topo R1)")
                else:
                    print(Fore.GREEN + f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | 🟢 COMPRA ATIVA")
                    
            elif ultimo_fechamento < ma9 and ma9 < ma21 and ifr > 35:
                # 🚨 3. FILTRO DE SEGURANÇA: BARREIRA DO SUPORTE S1
                if ultimo_fechamento <= (S1 * 1.0005):
                    print(f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | " + Fore.LIGHTBLACK_EX + "⏳ VENDA BARRADA (Preço colado no fundo S1)")
                else:
                    print(Fore.RED + f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | 🔴 VENDA ATIVA")
            else:
                print(f"{nome.ljust(15)}: {cifr} {ultimo_fechamento:,.2f} | IFR: {ifr:.1f} | " + Fore.LIGHTBLACK_EX + "⏳ NEUTRO")
                
        except Exception: continue
    print(f"\nVarredura concluída com proteção contra lateralização.")

try:
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        verificar_mercado()
        time.sleep(SEGUNDOS_ESPERA)
except KeyboardInterrupt:
    print("\nMonitoramento pausado.")
