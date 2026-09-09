import os
import glob
import io
import requests
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from database import DB_NAME, get_connection, sincronizar_usuarios_desde_xlsb

app = Flask(__name__)
app.secret_key = "myssa_portal_operativo_2026_seguro"

# 1. Enlace de SharePoint para EMO (Médico)
SHAREPOINT_EMO_URL = "https://myscia-my.sharepoint.com/:x:/g/personal/medico_mys_myssa_com_pe/IQAPaufD2Sy1S6VVCVNoI8gHAcMPjChMQ1ZoNfBLDhomzUo?e=hhqbbW&download=1"

# 2. Enlace de SharePoint para CAPACITACIONES
SHAREPOINT_CAP_URL = "https://myscia-my.sharepoint.com/:x:/g/personal/rrhh_condorcocha_myssa_com_pe/IQDwhxjC2UYpQbWUQKSwOIJlAasZOHewvkaHm6k8kHCEs7U?e=CNfQD7&download=1"

# Sincronización de credenciales de usuarios al arrancar
try:
    sincronizar_usuarios_desde_xlsb()
except Exception as e:
    print(f"Aviso al iniciar base de datos: {e}")

# ========================================================
# FUNCIÓN 1: OBTENER DATOS DE EMO (MÉDICO)
# ========================================================
def obtener_datos_emo(dni_usuario):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(SHAREPOINT_EMO_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []

        try:
            df = pd.read_excel(io.BytesIO(resp.content), header=4)
        except Exception:
            df = pd.read_excel(io.BytesIO(resp.content), header=4, engine="pyxlsb")

        df.columns = [str(c).strip().upper() for c in df.columns]

        col_dni = next((c for c in df.columns if "DNI" in c), None)
        col_emo = next((c for c in df.columns if "FECHA EM" in c or "EMO" in c), None)
        col_venc = next((c for c in df.columns if "VENCIMIENTO" in c), None)
        col_clinica = next((c for c in df.columns if "CLINIC" in c), None)

        if not (col_dni and col_emo and col_venc):
            return []

        df[col_dni] = df[col_dni].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)
        registros = df[df[col_dni] == str(dni_usuario).zfill(8)].copy()

        if registros.empty:
            return []

        registros["EMO_DT"] = pd.to_datetime(registros[col_emo], errors="coerce", dayfirst=True)
        registros = registros.sort_values(by="EMO_DT", ascending=False)

        def formatear_fecha(valor):
            if pd.isna(valor) or str(valor).strip() in ["", "-", "0"]:
                return "No registra"
            dt = pd.to_datetime(valor, errors="coerce", dayfirst=True)
            return dt.strftime("%d/%m/%Y") if pd.notna(dt) else str(valor).split()[0]

        examenes = []
        for _, fila in registros.iterrows():
            examenes.append({
                "fecha_emo": formatear_fecha(fila[col_emo]),
                "fecha_vencimiento": formatear_fecha(fila[col_venc]),
                "clinica": str(fila.get(col_clinica, "MEPSO")).strip() if col_clinica and pd.notna(fila[col_clinica]) else "No especificada"
            })
        return examenes
    except Exception as e:
        print(f"Error consultando EMO: {e}")
        return []

# ========================================================
# FUNCIÓN 2: OBTENER CAPACITACIONES DESDE SHAREPOINT
# ========================================================
def obtener_capacitaciones(dni_usuario):
    """Descarga el Excel de capacitaciones, busca en las 3 hojas y extrae los cursos desde INDUCCION DE SEGURIDAD ISEM."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(SHAREPOINT_CAP_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error descargando capacitaciones: {resp.status_code}")
            return []

        # Abrir el libro completo para leer las 3 hojas
        try:
            excel_obj = pd.ExcelFile(io.BytesIO(resp.content), engine="openpyxl")
        except Exception:
            excel_obj = pd.ExcelFile(io.BytesIO(resp.content), engine="pyxlsb")

        capacitaciones_registradas = []
        dni_buscado = str(dni_usuario).strip().zfill(8)

        # Recorrer cada hoja (Tabla1, Tabla2, Tabla3 o las que existan)
        for nombre_hoja in excel_obj.sheet_names:
            try:
                # Fila 5 es header=4 en pandas
                df = pd.read_excel(excel_obj, sheet_name=nombre_hoja, header=4)
                
                # Eliminar columnas totalmente vacías
                df = df.dropna(how="all", axis=1)

                # Limpieza de nombres de encabezados
                columnas_limpias = [" ".join(str(c).replace("\n", " ").split()).strip() for c in df.columns]
                df.columns = columnas_limpias

                # Buscar columna DNI
                col_dni = next((c for c in df.columns if "DNI" in c.upper()), None)
                if not col_dni:
                    continue

                # Normalizar columna DNI
                df[col_dni] = df[col_dni].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)

                # Buscar fila del usuario
                filas_usuario = df[df[col_dni] == dni_buscado]
                if filas_usuario.empty:
                    continue

                # Identificar a partir de qué columna empiezan las capacitaciones
                # Regla: Desde "INDUCCION DE SEGURIDAD ISEM" en adelante
                idx_inicio_cursos = None
                for idx, c in enumerate(df.columns):
                    c_up = c.upper()
                    if "INDUCCION" in c_up and "ISEM" in c_up:
                        idx_inicio_cursos = idx
                        break
                    elif "INDUCCION" in c_up:
                        idx_inicio_cursos = idx
                        break

                # Si no encuentra el texto exacto, tomar las que siguen después de CARGO o columna 5
                if idx_inicio_cursos is None:
                    idx_inicio_cursos = 5

                columnas_cursos = list(df.columns)[idx_inicio_cursos:]

                # Extraer los cursos de la fila encontrada
                for _, fila in filas_usuario.iterrows():
                    for curso in columnas_cursos:
                        # Omitir nombres irrelevantes o vacíos
                        if "UNNAMED" in curso.upper():
                            continue

                        valor_celda = fila.get(curso)

                        # Si la celda tiene un valor registrado (no nulo, no guion, no cero)
                        if pd.notna(valor_celda):
                            val_str = str(valor_celda).strip()
                            if val_str not in ["", "-", "0", "0.0", "NO", "NONE", "NAN"]:
                                # Formatear si es fecha
                                dt = pd.to_datetime(valor_celda, errors="coerce", dayfirst=True)
                                fecha_formateada = dt.strftime("%d/%m/%Y") if pd.notna(dt) else val_str

                                capacitaciones_registradas.append({
                                    "curso": curso,
                                    "fecha": fecha_formateada,
                                    "origen": nombre_hoja
                                })
            except Exception as err_hoja:
                print(f"Error procesando hoja {nombre_hoja}: {err_hoja}")
                continue

        return capacitaciones_registradas

    except Exception as e:
        print(f"Error general en capacitaciones: {e}")
        return []

# ========================================================
# RUTAS FLASK
# ========================================================
@app.route("/")
def home():
    error = request.args.get("error")
    datos_emo = []
    datos_cap = []

    # Si hay sesión iniciada, buscar sus datos en ambos SharePoints
    if session.get("user_dni"):
        dni = session.get("user_dni")
        datos_emo = obtener_datos_emo(dni)
        datos_cap = obtener_capacitaciones(dni)

    return render_template("index.html", error=error, emo=datos_emo, capacitaciones=datos_cap)

@app.route("/login", methods=["POST"])
def login():
    dni_input = request.form.get("username", "").strip()
    password_input = request.form.get("password", "").strip()

    if dni_input.isdigit() and len(dni_input) < 8:
        dni_input = dni_input.zfill(8)

    try:
        conn = get_connection()
        usuario = conn.execute("SELECT * FROM usuarios WHERE dni = ?", (dni_input,)).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["password_hash"], password_input):
            session["user_dni"] = usuario["dni"]
            session["nombre_completo"] = usuario["nombre_completo"]
            session["cargo"] = usuario["cargo"]
            return redirect(url_for("home"))
        else:
            return redirect(url_for("home", error="DNI o contraseña incorrectos."))
    except Exception as err:
        return redirect(url_for("home", error=f"Error del sistema: {err}"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
