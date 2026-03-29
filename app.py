import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SICOP Analytics", layout="wide")

EXPECTED_COLUMNS = [
    "NRO_SICOP",
    "NUMERO_LINEA",
    "NUMERO_PARTIDA",
    "DESC_LINEA",
    "CEDULA_INSTITUCION",
    "NRO_PROCEDIMIENTO",
    "TIPO_PROCEDIMIENTO",
    "FECHA_PUBLICACION",
]


def extract_sheet_id(url: str) -> Optional[str]:
    """Extract Google Sheets ID from a full URL or return plain ID if given."""
    text = url.strip()
    id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", text)
    if id_match:
        return id_match.group(1)

    if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", text):
        return text

    parsed = urlparse(text)
    query_params = parse_qs(parsed.query)
    key = query_params.get("key", [None])[0]
    if key:
        return key

    return None


def sheet_csv_url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


@st.cache_data(show_spinner=False)
def load_sheet_data(source: str) -> pd.DataFrame:
    sheet_id = extract_sheet_id(source)
    if not sheet_id:
        raise ValueError("No se pudo extraer el ID de Google Sheets.")

    df = pd.read_csv(sheet_csv_url(sheet_id), dtype=str)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas esperadas: " + ", ".join(missing)
        )

    # Normalize data types
    df = df.copy()
    df["FECHA_PUBLICACION"] = pd.to_datetime(df["FECHA_PUBLICACION"], errors="coerce")
    for col in ["NUMERO_LINEA", "NUMERO_PARTIDA"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")

    tipo_opts = sorted(df["TIPO_PROCEDIMIENTO"].dropna().unique().tolist())
    tipo_sel = st.sidebar.multiselect("Tipo de procedimiento", tipo_opts, default=tipo_opts)

    name_columns = [
        "NOMBRE_INSTITUCION",
        "INSTITUCION",
        "NOMBRE_ENTIDAD",
        "NOMBRE_INSTITUCION_PUBLICA",
    ]
    institution_name_col = next((col for col in name_columns if col in df.columns), None)

    if institution_name_col:
        inst_catalog = (
            df[[institution_name_col, "CEDULA_INSTITUCION"]]
            .dropna(subset=[institution_name_col])
            .drop_duplicates()
            .copy()
        )
        inst_catalog = inst_catalog.sort_values(
            [institution_name_col, "CEDULA_INSTITUCION"], na_position="last"
        )
        inst_catalog["inst_label"] = inst_catalog.apply(
            lambda row: (
                f"{row[institution_name_col]} ({row['CEDULA_INSTITUCION']})"
                if pd.notna(row["CEDULA_INSTITUCION"])
                else str(row[institution_name_col])
            ),
            axis=1,
        )
        inst_opts = inst_catalog["inst_label"].tolist()
        inst_sel = st.sidebar.multiselect(
            "Institución", inst_opts, default=inst_opts
        )

        if not inst_catalog.empty:
            st.sidebar.caption("Relación de institución pública y cédula.")
            st.sidebar.dataframe(
                inst_catalog.rename(
                    columns={
                        institution_name_col: "Institución",
                        "CEDULA_INSTITUCION": "Cédula",
                    }
                )[["Institución", "Cédula"]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        inst_opts = sorted(df["CEDULA_INSTITUCION"].dropna().unique().tolist())
        inst_sel = st.sidebar.multiselect(
            "Cédula institución", inst_opts, default=inst_opts
        )

    date_min = df["FECHA_PUBLICACION"].min()
    date_max = df["FECHA_PUBLICACION"].max()

    if pd.notna(date_min) and pd.notna(date_max):
        date_sel = st.sidebar.date_input(
            "Rango de publicación", value=(date_min.date(), date_max.date())
        )
    else:
        date_sel = None

    filtered = df.copy()
    if tipo_sel:
        filtered = filtered[filtered["TIPO_PROCEDIMIENTO"].isin(tipo_sel)]
    if inst_sel:
        if institution_name_col:
            selected_ids = set(
                inst_catalog.loc[
                    inst_catalog["inst_label"].isin(inst_sel), "CEDULA_INSTITUCION"
                ]
                .dropna()
                .tolist()
            )
            selected_names = set(
                inst_catalog.loc[
                    inst_catalog["inst_label"].isin(inst_sel), institution_name_col
                ]
                .dropna()
                .tolist()
            )
            filtered = filtered[
                filtered["CEDULA_INSTITUCION"].isin(selected_ids)
                | filtered[institution_name_col].isin(selected_names)
            ]
        else:
            filtered = filtered[filtered["CEDULA_INSTITUCION"].isin(inst_sel)]

    if date_sel and len(date_sel) == 2:
        start_dt = pd.to_datetime(date_sel[0])
        end_dt = pd.to_datetime(date_sel[1])
        filtered = filtered[
            (filtered["FECHA_PUBLICACION"].notna())
            & (filtered["FECHA_PUBLICACION"] >= start_dt)
            & (filtered["FECHA_PUBLICACION"] <= end_dt)
        ]

    return filtered


def kpi_block(df: pd.DataFrame) -> None:
    total_registros = len(df)
    total_procedimientos = df["NRO_PROCEDIMIENTO"].nunique(dropna=True)
    total_sicop = df["NRO_SICOP"].nunique(dropna=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros", f"{total_registros:,}")
    c2.metric("Procedimientos únicos", f"{total_procedimientos:,}")
    c3.metric("NRO_SICOP únicos", f"{total_sicop:,}")


def charts(df: pd.DataFrame) -> None:
    st.subheader("Distribución por tipo de procedimiento")
    by_type = (
        df.groupby("TIPO_PROCEDIMIENTO", dropna=False)
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )
    fig_type = px.bar(by_type, x="TIPO_PROCEDIMIENTO", y="cantidad")
    st.plotly_chart(fig_type, use_container_width=True)

    st.subheader("Evolución temporal de publicaciones")
    time_data = df.dropna(subset=["FECHA_PUBLICACION"]).copy()
    if not time_data.empty:
        time_data["mes"] = time_data["FECHA_PUBLICACION"].dt.to_period("M").astype(str)
        by_month = time_data.groupby("mes").size().reset_index(name="cantidad")
        fig_time = px.line(by_month, x="mes", y="cantidad", markers=True)
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay fechas válidas para graficar la evolución temporal.")


st.title("Analizador de datos SICOP")
st.caption("Conecta una hoja de Google Sheets y explora tus datos de compras públicas.")

DEFAULT_SHEET = "https://docs.google.com/spreadsheets/d/1bXoT3eI0ku2d2nkFW2PEsEHGowC98Yho0VjZYt1BXcw/edit?usp=sharing"
source = st.text_input("URL o ID de Google Sheets", value=DEFAULT_SHEET)

if source:
    try:
        data = load_sheet_data(source)
        filtered_data = apply_filters(data)

        kpi_block(filtered_data)
        charts(filtered_data)

        st.subheader("Datos filtrados")
        st.dataframe(filtered_data, use_container_width=True)

        csv_data = filtered_data.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar CSV filtrado",
            data=csv_data,
            file_name="sicop_filtrado.csv",
            mime="text/csv",
        )
    except Exception as exc:
        st.error(f"No se pudo cargar la hoja: {exc}")
