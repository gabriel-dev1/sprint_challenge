import json
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# -------------------- Configuração --------------------
ROOT = Path(__file__).parent
MOCK_PATH = ROOT / "data" / "mock_today.json"

# -------------------- Funções --------------------
def carregar_mock(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Arquivo mock não encontrado: {path}")
        return pd.DataFrame()
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    df = pd.DataFrame(payload["data"])
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"]).dt.tz_convert(None)
    df.attrs["meta"] = {
        "plant_id": payload.get("plant_id"),
        "inverter_sn": payload.get("inverter_sn"),
        "date": payload.get("date"),
        "timezone": payload.get("timezone"),
        "units": payload.get("units", {})
    }
    return df

def resumo_dia(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    energia_dia = float(df["Eday"].dropna().iloc[-1]) if "Eday" in df.columns else 0.0
    soc_ini = int(df["Cbattery1"].dropna().iloc[0]) if "Cbattery1" in df.columns else 0
    soc_fim = int(df["Cbattery1"].dropna().iloc[-1]) if "Cbattery1" in df.columns else 0
    equi = f"{df.attrs["meta"]["inverter_sn"]}"
    pico = float(df["Pac"].max()) if "Pac" in df.columns else 0.0
    return {
        "energia_dia": energia_dia,
        "soc_ini": soc_ini,
        "soc_fim": soc_fim,
        "pico_potencia": pico,
        "equipamento": equi
    }

def kwh(x: float) -> str:
    return f"{x:,.2f} kWh".replace(",", "X").replace(".", ",").replace("X", ".")

def kw(x: float) -> str:
    return f"{x:,.2f} kW".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------------- Carrega mock --------------------
df = carregar_mock(MOCK_PATH)

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="Energia Assistant", layout="wide", page_icon="⚡")
st.title("⚡ Energia Assistant — Mock")

if df.empty:
    st.warning("Nenhum dado encontrado no arquivo mock.json.")
else:
    df_sel = df.copy()

    # KPIs
    res = resumo_dia(df_sel)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Energia do dia", kwh(res.get("energia_dia", 0.0)))
    col2.metric("SOC inicial → final", f"{res.get('soc_ini',0)}% → {res.get('soc_fim',0)}%")
    col3.metric("Pico de energia", kw(res.get("pico_potencia",0.0)))
    col4.metric("Inversor", f"{res.get("equipamento")}")

    # Gráficos
    left, right = st.columns(2)
    with left:
        if "Pac" in df_sel.columns:
            fig_p = px.line(df_sel, x="time", y="Pac", markers=True, title="Potência (Pac) ao longo do dia")
            st.plotly_chart(fig_p, use_container_width=True)
    with right:
        if "Cbattery1" in df_sel.columns:
            fig_soc = px.line(df_sel, x="time", y="Cbattery1", markers=True, title="Estado de Carga da Bateria (SOC %)")
            st.plotly_chart(fig_soc, use_container_width=True)

    # Tabela
    with st.expander("Ver tabela de dados"):
        st.dataframe(df_sel, use_container_width=True, hide_index=True)

if st.button("Enviar dados"):
    payload = {"equipamento": df[col4].values, "energia": df[col1].values}
    try:
        resposta = requests.post("https://sprint-challenge.onrender.com/enviar", json=payload)
        if resposta.status_code == 200:
            st.success("✅ Dados enviados com sucesso!")
            st.json(resposta.json())
        else:
            st.error(f"Erro: {resposta.status_code}")
    except Exception as e:
        st.error(f"Falha na conexão: {e}")