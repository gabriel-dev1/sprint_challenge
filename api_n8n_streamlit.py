import json
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import uvicorn

# -------------------- Configuração --------------------
ROOT = Path(__file__).parent
MOCK_PATH = ROOT / "data" / "mock_today.json"

# -------------------- Função para carregar mock --------------------
def carregar_mock(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"Arquivo mock não encontrado: {path}")
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

# -------------------- Resumo diário --------------------
def resumo_dia(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    energia_dia = float(df["Eday"].dropna().iloc[-1]) if "Eday" in df.columns else 0.0
    soc_ini = int(df["Cbattery1"].dropna().iloc[0]) if "Cbattery1" in df.columns else 0
    soc_fim = int(df["Cbattery1"].dropna().iloc[-1]) if "Cbattery1" in df.columns else 0
    pico = float(df["Pac"].max()) if "Pac" in df.columns else 0.0
    return {
        "energia_dia": energia_dia,
        "soc_ini": soc_ini,
        "soc_fim": soc_fim,
        "pico_potencia": pico
    }

# -------------------- FastAPI --------------------
app = FastAPI()
df = carregar_mock(MOCK_PATH)


'''@app.get("/dados-energia")
def get_dados_energia():
    if df.empty:
        return {"error": "Nenhum dado disponível"}
    df_envio = df.copy()
    df_envio["time"] = df_envio["time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    resumo = resumo_dia(df_envio)
    payload = {
        "plant_id": str(df.attrs["meta"].get("plant_id", "")),
        "inverter_sn": str(df.attrs["meta"].get("inverter_sn", "")),
        "date": str(df.attrs["meta"].get("date", "")),
        "energia_total": float(resumo.get("energia_dia", 0.0)),
        "soc_ini": int(resumo.get("soc_ini", 0)),
        "soc_fim": int(resumo.get("soc_fim", 0)),
        "pico_potencia": float(resumo.get("pico_potencia", 0.0)),
        "data": df_envio.to_dict(orient="records")
    }
    return payload '''

df_envio = df.copy()
resumo = resumo_dia(df_envio)

# Modelo de dados esperado
class Dados(BaseModel):
    energia_total: float = float(resumo.get("energia_dia", 0.0))
    inverter_sn: str = str(df.attrs["meta"].get("inverter_sn", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou coloque o domínio do Streamlit
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "API funcionando"}

dados_recebidos = []

# Rota para receber dados do Streamlit
@app.post("/enviar/")
async def receber_dados(dados: Dados): # dados: Dados request: Request
    print(f"Recebido: {dados.inverter_sn}, {dados.energia_total}")
    dados_recebidos.append(dados)
    #return {"status": "ok", "mensagem": f"Dados recebidos de {dados.inverter_sn}"}
    return {
        "status": "ok",
        "mensagem": "Dados recebidos com sucesso",
        "inverter_sn": dados.inverter_sn,
        "energia_total": dados.energia_total
    }

def mostrar_dados():
    return dados_recebidos

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
