import yfinance as yf
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
import pytz
from colorama import init, Fore, Style

init(autoreset=True)

PERFIL_OPERACIONAL = 'MESA_QUANT_TOTAL_V35'
TEMPO_GRAFICO = '15m'
SEGUNDOS_ESPERA = 300  
META_DIARIA = 200.0

fuso_br = pytz.timezone('America/Sao_Paulo')

def puxar_dados_isolados(ticker):
    try:
        t = yf.Ticker(ticker)
        df_i = t.history(period='5d', interval=TEMPO_GRAFICO)
        df_d = t.history(period='5d', interval='1d')
        
        if df_i.empty or df_d.empty: return 0.0, 0.0, 0.0, 0.0, 0.0
        
        preco_atual = float(df_i['Close'].dropna().values[-1])
        retorno = float((preco_atual / float(df_i['Close'].dropna().values[-20]) - 1) * 100)
        
        high_ant = float(df_d['High'].dropna().values[-2])
        low_ant = float(df_d['Low'].dropna().values[-2])
        close_ant = float(df_d['Close'].dropna().values[-2])
        
        P = (high_ant + low_ant + close_ant) / 3
        S1 = (2 * P) - high_ant
        R1 = (2 * P) - low_ant
        
        return retorno, preco_atual, P, S1, R1
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 0.0

def exibir_boleta_cirurgica(operacao, at1, at2, p1, p2, r1, s1, p_p1, p_p2, tipo_mercado):
    print(Fore.GREEN + f"\n🎯 [GATILHO CIRÚRGICO ATIVO]: {operacao}")
    print("-" * 60)
    
    if tipo_mercado == "INDICES":
        sl_c = p1 - abs(p1 - p_p1) * 0.4
        sl_v = p2 + abs(p2 - p_p2) * 0.4
    else:
        sl_c = p1 - (p1 * 0.002)
        sl_v = p2 + (p2 * 0.002)

    print(Fore.LIGHTGREEN_EX + f"🟢 COMPRA: {at1.ljust(12)} | Preço: {p1:.4f} | ALVO TP: {r1:.4f} | STOP: {sl_c:.4f}")
    print(Fore.LIGHTRED_EX + f"🔴 VENDA : {at2.ljust(12)} | Preço: {p2:.4f} | ALVO TP: {s1:.4f} | STOP: {sl_v:.4f}")

def verificar_mercado():
    print(Fore.GREEN + "============================================================")
    print(Fore.GREEN + "   📡 RANGER QUANT RADAR v35.0 - ENGINE TOTAL TERM          ")
    print(Fore.GREEN + "============================================================")
    print(f"Relógio Sistema: {datetime.now(fuso_br).strftime('%H:%M:%S')} | Meta: US$ {META_DIARIA}/dia")
    print("-" * 60)

    # 📊 MATRIZ 1: ÍNDICES (Triple-Spread com Dow Jones)
    ret_nq, p_nq, piv_nq, s1_nq, r1_nq = puxar_dados_isolados('NQ=F')
    ret_es, p_es, piv_es, s1_es, r1_es = puxar_dados_isolados('ES=F')
    ret_ym, p_ym, piv_ym, s1_ym, r1_ym = puxar_dados_isolados('YM=F')
    
    spread_es_nq = ret_es - ret_nq
    spread_ym_nq = ret_ym - ret_nq
    
    print(Fore.YELLOW + "📊 [MATRIZ 1] TRIPLE-SPREAD DE ÍNDICES DE NOVA YORK:")
    if p_nq > 0 and p_es > 0 and p_ym > 0:
        print(f"NQ: {p_nq:,.2f} ({ret_nq:+.2f}%) | ES: {p_es:,.2f} ({ret_es:+.2f}%) | YM(US30): {p_ym:,.2f} ({ret_ym:+.2f}%)")
        print(f"Spread (S&P vs NQ): {spread_es_nq:+.2f}% | Spread (Dow vs NQ): {spread_ym_nq:+.2f}%")
        
        if spread_ym_nq > 0.40:
            exibir_boleta_cirurgica("ARBITRAGEM DOW/NASDAQ", "Dow Jones (US30)", "Nasdaq 100", p_ym, p_nq, r1_ym, s1_nq, piv_ym, piv_nq, "INDICES")
        elif spread_es_nq > 0.35:
            exibir_boleta_cirurgica("ARBITRAGEM S&P/NASDAQ", "S&P 500", "Nasdaq 100", p_es, p_nq, r1_es, s1_nq, piv_es, piv_nq, "INDICES")
        elif spread_ym_nq < -0.40:
            exibir_boleta_cirurgica("ARBITRAGEM NASDAQ/DOW", "Nasdaq 100", "Dow Jones (US30)", p_nq, p_ym, r1_nq, s1_ym, piv_nq, piv_ym, "INDICES")
        else:
            print(Fore.LIGHTBLACK_EX + f"⏳ Índices em Equilíbrio. Alvos -> NQ R1: {r1_nq:,.1f} S1: {s1_nq:,.1f} | ES R1: {r1_es:,.1f} | YM R1: {r1_ym:,.1f}")
    else: print(Fore.RED + "Aguardando dados de Chicago...")
    print("-" * 60)

    # 💱 MATRIZ 2: FOREX
    ret_eur, p_eur, piv_eur, s1_eur, r1_eur = puxar_dados_isolados('EURUSD=X')
    ret_gbp, p_gbp, piv_gbp, s1_gbp, r1_gbp = puxar_dados_isolados('GBPUSD=X')
    spread_forex = ret_gbp - ret_eur
    
    print(Fore.YELLOW + "💱 [MATRIZ 2] SPREAD FOREX MAJORS:")
    if p_eur > 0 and p_gbp > 0:
        print(f"EUR: {p_eur:.4f} ({ret_eur:+.2f}%) | GBP: {p_gbp:.4f} ({ret_gbp:+.2f}%) | Spread: {spread_forex:+.2f}%")
        if spread_forex > 0.12:
            exibir_boleta_cirurgica("ARBITRAGEM CÂMBIO", "GBP/USD", "EUR/USD", p_gbp, p_eur, r1_gbp, s1_eur, piv_gbp, piv_eur, "FOREX")
        elif spread_forex < -0.12:
            exibir_boleta_cirurgica("ARBITRAGEM CÂMBIO", "EUR/USD", "GBP/USD", p_eur, p_gbp, r1_eur, s1_gbp, piv_eur, piv_gbp, "FOREX")
        else:
            print(Fore.LIGHTBLACK_EX + f"⏳ Equilíbrio. Alvos -> EUR R1: {r1_eur:.4f} S1: {s1_eur:.4f} | GBP R1: {r1_gbp:.4f} S1: {s1_gbp:.4f}")
    else: print(Fore.RED + "Aguardando dados de Londres...")
    print("-" * 60)

    # 🛢️ MATRIZ 3: ENERGIA
    ret_wti, p_wti, piv_wti, s1_wti, r1_wti = puxar_dados_isolados('CL=F')
    ret_ng, p_ng, piv_ng, s1_ng, r1_ng = puxar_dados_isolados('NG=F')
    spread_energia = ret_wti - ret_ng
    
    print(Fore.YELLOW + "🛢️ [MATRIZ 3] COMBUSTÍVEIS DE ENERGIA:")
    if p_wti > 0 and p_ng > 0:
        print(f"WTI: US$ {p_wti:,.2f} ({ret_wti:+.2f}%) | NG: US$ {p_ng:,.3f} ({ret_ng:+.2f}%) | Spread: {spread_energia:+.2f}%")
        if spread_energia > 1.20:
            exibir_boleta_cirurgica("SPREAD ENERGIA", "Petróleo WTI", "Gás Natural", p_wti, p_ng, r1_wti, s1_ng, piv_wti, piv_ng, "ENERGIA")
        elif spread_energia < -1.20:
            exibir_boleta_cirurgica("SPREAD ENERGIA", "Gás Natural", "Petróleo WTI", p_ng, p_wti, r1_ng, s1_wti, piv_ng, piv_wti, "ENERGIA")
        else:
            print(Fore.LIGHTBLACK_EX + f"⏳ Equilíbrio. Alvos -> WTI R1: {r1_wti:,.2f} S1: {s1_wti:,.2f} | NG R1: {r1_ng:,.3f} S1: {s1_ng:,.3f}")
    else: print(Fore.RED + "Aguardando dados de energia...")
    print("-" * 60)

    # 🪙 MATRIZ 4: METAIS
    ret_gc, p_gc, piv_gc, s1_gc, r1_gc = puxar_dados_isolados('GC=F')
    ret_si, p_si, piv_si, s1_si, r1_si = puxar_dados_isolados('SI=F')
    spread_metais = ret_gc - ret_si
    
    print(Fore.YELLOW + "🪙 [MATRIZ 4] METAIS PRECIOSOS:")
    if p_gc > 0 and p_si > 0:
        print(f"Ouro: US$ {p_gc:,.2f} ({ret_gc:+.2f}%) | Prata: US$ {p_si:,.2f} ({ret_si:+.2f}%) | Spread: {spread_metais:+.2f}%")
        if spread_metais > 0.60:
            exibir_boleta_cirurgica("SPREAD METAIS", "Ouro Macro", "Prata Metal", p_gc, p_si, r1_gc, s1_si, piv_gc, piv_si, "METAIS")
        elif spread_metais < -0.60:
            exibir_boleta_cirurgica("SPREAD METAIS", "Prata Metal", "Ouro Macro", p_si, p_gc, r1_si, s1_gc, piv_si, piv_gc, "METAIS")
        else:
            print(Fore.LIGHTBLACK_EX + f"⏳ Equilíbrio. Alvos -> Ouro R1: {r1_gc:,.1f} S1: {s1_gc:,.1f} | Prata R1: {r1_si:,.2f} S1: {s1_si:,.2f}")
    else: print(Fore.RED + "Aguardando dados de metais...")
    print("-" * 60)

    print("Matriz multi-spread v35.0 terminal operando com sucesso.")

try:
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        verificar_mercado()
        time.sleep(SEGUNDOS_ESPERA)
except KeyboardInterrupt:
    print("\nMonitoramento quantitativo pausado.")
