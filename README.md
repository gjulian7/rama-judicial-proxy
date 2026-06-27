# Rama Judicial Proxy for Render

Small FastAPI proxy for the Rama Judicial process search API.

## Render settings

Runtime: Python

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Environment variables:

```text
RAMA_PROXY_KEY = generate a long private value
DEFAULT_NOMBRE = SEVEN ELEPHANTS
DEFAULT_TIPO_PERSONA = jur
DEFAULT_CODIFICACION_DESPACHO = 05
```

## Test after deployment

Replace the URL and key:

```bash
curl -H "X-API-Key: your-secret-key" "https://your-service.onrender.com/rama/seven-elephants"
```

Generic endpoint:

```bash
curl -H "X-API-Key: your-secret-key" "https://your-service.onrender.com/rama/procesos?nombre=SEVEN%20ELEPHANTS"
```

Health check:

```text
/healthz
```
