import os
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Rama Judicial Proxy", version="1.1.0")

RAMA_URL = "https://consultaprocesos.ramajudicial.gov.co:448/api/v2/Procesos/Consulta/NombreRazonSocial"

DEFAULT_NOMBRE = os.getenv("DEFAULT_NOMBRE", "SEVEN ELEPHANTS")
DEFAULT_TIPO_PERSONA = os.getenv("DEFAULT_TIPO_PERSONA", "jur")
DEFAULT_CODIFICACION_DESPACHO = os.getenv("DEFAULT_CODIFICACION_DESPACHO", "05")
RAMA_PROXY_KEY = os.getenv("RAMA_PROXY_KEY")

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://consultaprocesos.ramajudicial.gov.co/procesos/Index",
    "Origin": "https://consultaprocesos.ramajudicial.gov.co",
}


def require_api_key(x_api_key: Optional[str]) -> None:
    if not RAMA_PROXY_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is missing RAMA_PROXY_KEY environment variable.",
        )

    if x_api_key != RAMA_PROXY_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def fetch_page(
    nombre: str,
    tipo_persona: str,
    solo_activos: bool,
    codificacion_despacho: str,
    pagina: int,
) -> dict:
    params = {
        "nombre": nombre,
        "tipoPersona": tipo_persona,
        "SoloActivos": str(solo_activos).lower(),
        "codificacionDespacho": codificacion_despacho,
        "pagina": pagina,
    }

    try:
        response = requests.get(
            RAMA_URL,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Could not reach Rama Judicial API.",
                "error": str(exc),
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Rama Judicial API returned an error.",
                "status_code": response.status_code,
                "body": response.text[:1000],
            },
        )

    try:
        return response.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Rama Judicial API did not return valid JSON.",
                "body": response.text[:1000],
            },
        )


def normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value[:10]


def build_consulta_response(
    nombre: str,
    tipo_persona: str,
    solo_activos: bool,
    codificacion_despacho: str,
) -> JSONResponse:
    first_page = fetch_page(
        nombre=nombre,
        tipo_persona=tipo_persona,
        solo_activos=solo_activos,
        codificacion_despacho=codificacion_despacho,
        pagina=1,
    )

    paginacion = first_page.get("paginacion", {}) or {}
    cantidad_paginas = int(paginacion.get("cantidadPaginas") or 1)

    procesos = list(first_page.get("procesos", []) or [])

    for pagina in range(2, cantidad_paginas + 1):
        page_data = fetch_page(
            nombre=nombre,
            tipo_persona=tipo_persona,
            solo_activos=solo_activos,
            codificacion_despacho=codificacion_despacho,
            pagina=pagina,
        )
        procesos.extend(page_data.get("procesos", []) or [])

    most_recent = None
    for proceso in procesos:
        fecha = proceso.get("fechaUltimaActuacion")
        if fecha and (most_recent is None or fecha > most_recent):
            most_recent = fecha

    clean_procesos = []
    for proceso in procesos:
        fecha_ultima = proceso.get("fechaUltimaActuacion")
        clean_procesos.append(
            {
                "llaveProceso": proceso.get("llaveProceso"),
                "despacho": (proceso.get("despacho") or "").strip(),
                "sujetosProcesales": proceso.get("sujetosProcesales"),
                "fechaProceso": normalize_date(proceso.get("fechaProceso")),
                "fechaUltimaActuacion": normalize_date(fecha_ultima),
                "esMasReciente": fecha_ultima == most_recent,
            }
        )

    return JSONResponse(
        {
            "tipoConsulta": "NombreRazonSocial",
            "nombre": nombre,
            "parametros": {
                "tipoPersona": tipo_persona,
                "soloActivos": solo_activos,
                "codificacionDespacho": codificacion_despacho,
            },
            "paginacion": {
                "cantidadPaginas": cantidad_paginas,
                "cantidadRegistrosOriginal": paginacion.get("cantidadRegistros"),
            },
            "totalProcesos": len(clean_procesos),
            "fechaUltimaActuacionMasReciente": normalize_date(most_recent),
            "procesos": clean_procesos,
            "retrievedAt": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/")
def root():
    return {
        "service": "rama judicial proxy",
        "status": "ok",
        "docs": "/docs",
        "publicEndpoint": "/rama/public/seven-elephants",
        "protectedEndpoint": "/rama/seven-elephants",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/rama/procesos")
def consulta_procesos(
    nombre: str = Query(DEFAULT_NOMBRE),
    tipoPersona: str = Query(DEFAULT_TIPO_PERSONA),
    soloActivos: bool = Query(False),
    codificacionDespacho: str = Query(DEFAULT_CODIFICACION_DESPACHO),
    x_api_key: Optional[str] = Header(default=None),
):
    require_api_key(x_api_key)

    return build_consulta_response(
        nombre=nombre,
        tipo_persona=tipoPersona,
        solo_activos=soloActivos,
        codificacion_despacho=codificacionDespacho,
    )


@app.get("/rama/seven-elephants")
def consulta_seven_elephants(x_api_key: Optional[str] = Header(default=None)):
    require_api_key(x_api_key)

    return build_consulta_response(
        nombre=DEFAULT_NOMBRE,
        tipo_persona=DEFAULT_TIPO_PERSONA,
        solo_activos=False,
        codificacion_despacho=DEFAULT_CODIFICACION_DESPACHO,
    )


@app.get("/rama/public/seven-elephants")
def consulta_publica_seven_elephants():
    """
    Public, narrow endpoint for normal browser access and normal ChatGPT browsing.

    This endpoint does not accept arbitrary search parameters.
    It only checks the configured Seven Elephants search.
    """
    return build_consulta_response(
        nombre=DEFAULT_NOMBRE,
        tipo_persona=DEFAULT_TIPO_PERSONA,
        solo_activos=False,
        codificacion_despacho=DEFAULT_CODIFICACION_DESPACHO,
    )
