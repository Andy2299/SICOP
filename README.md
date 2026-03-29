# SICOP Analytics App

Aplicación en **Streamlit** para analizar datos de SICOP desde una hoja en Google Sheets y verla en navegador web.

## Requisitos

- Python 3.10+

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar en web local (navegador)

```bash
streamlit run app.py
```

Luego abrir en tu navegador:
- `http://localhost:8501`

## Ejecutar con Docker (ideal para servidor/web)

```bash
docker build -t sicop-analytics .
docker run -p 8501:8501 sicop-analytics
```

Luego abrir:
- `http://localhost:8501`

## Despliegue web rápido (sin servidor propio)

Puedes publicarla en:
- **Streamlit Community Cloud** (conectando este repo).
- **Render / Railway / Fly.io** usando el `Dockerfile` incluido.

## Datos esperados

La hoja debe contener los siguientes encabezados:

- `NRO_SICOP`
- `NUMERO_LINEA`
- `NUMERO_PARTIDA`
- `DESC_LINEA`
- `CEDULA_INSTITUCION`
- `NRO_PROCEDIMIENTO`
- `TIPO_PROCEDIMIENTO`
- `FECHA_PUBLICACION`

## Funcionalidades

- Conexión directa a Google Sheets (URL o ID).
- Filtros por tipo de procedimiento, institución y rango de fechas.
- KPIs principales.
- Gráficos de distribución y evolución temporal.
- Exportación de datos filtrados a CSV.
