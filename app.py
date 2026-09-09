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

try:
    sincronizar_usuarios_desde_xlsb()
except Exception as e:
    print(f"Aviso al iniciar base de datos: {e}")

# ========================================================
# FUNCIÓN 1: CONSULTA DE EMO
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
                "clinica": str(fila.get(col_clinica, "MEPSO")).strip() if col_clinica and pd.notna(fila[col_clinica]) else "MEPSO"
            })
        return examenes
    except Exception as e:
        print(f"Error consultando EMO: {e}")
        return []

# ========================================================
# FUNCIÓN 2: CONSULTA DE CAPACITACIONES REALES
# ========================================================
def obtener_capacitaciones(dni_usuario):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(SHAREPOINT_CAP_URL, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error descargando capacitaciones: {resp.status_code}")
            return []

        # Abrir archivo para leer todas las hojas
        try:
            excel_obj = pd.ExcelFile(io.BytesIO(resp.content), engine="openpyxl")
        except Exception:
            excel_obj = pd.ExcelFile(io.BytesIO(resp.content), engine="pyxlsb")

        capacitaciones = []
        dni_buscado = str(dni_usuario).strip().zfill(8)

        for sheet in excel_obj.sheet_names:
            try:
                # Fila 5 de Excel corresponde a header=4 en pandas
                df = pd.read_excel(excel_obj, sheet_name=sheet, header=4)
                df = df.dropna(how="all", axis=1)
                df.columns = [" ".join(str(c).replace("\n", " ").split()).strip() for c in df.columns]

                # Ubicar columna DNI
                col_dni = next((c for c in df.columns if "DNI" in c.upper()), None)
                if not col_dni:
                    continue

                df[col_dni] = df[col_dni].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)
                filas_persona = df[df[col_dni] == dni_buscado]
                if filas_persona.empty:
                    continue

                # Ubicar desde INDUCCION DE SEGURIDAD ISEM en adelante
                idx_inicio = None
                for idx, col in enumerate(df.columns):
                    col_u = col.upper()
                    if "INDUCCION" in col_u and "ISEM" in col_u:
                        idx_inicio = idx
                        break

                if idx_inicio is None:
                    # Alternativa por si varía el nombre exacto
                    for idx, col in enumerate(df.columns):
                        if "INDUCCION" in col.upper():
                            idx_inicio = idx
                            break

                if idx_inicio is None:
                    idx_inicio = 6

                columnas_cursos = list(df.columns)[idx_inicio:]

                for _, fila in filas_persona.iterrows():
                    for curso in columnas_cursos:
                        if "UNNAMED" in curso.upper():
                            continue

                        valor = fila.get(curso)
                        valor_str = str(valor).strip().upper() if pd.notna(valor) else ""

                        # 1. Descartar vacíos o guiones
                        if valor_str in ["", "-", "NAN", "NONE", "0", "0.0"]:
                            continue

                        # 2. Casos donde NO APLICA al puesto
                        if "NA" in valor_str or "N/A" in valor_str:
                            capacitaciones.append({
                                "curso": curso,
                                "fecha": "No Aplica",
                                "estado": "NO APLICA",
                                "clase": "tag-noaplica",
                                "origen": sheet
                            })

                        # 3. Casos donde la fecha dice FALTA
                        elif "FALTA" in valor_str:
                            # ---> SI DESEAS MOSTRARLO COMO PENDIENTE (Recomendado):
                            capacitaciones.append({
                                "curso": curso,
                                "fecha": "Falta completar",
                                "estado": "PENDIENTE",
                                "clase": "tag-pendiente",
                                "origen": sheet
                            })

                            # ---> SI EN CAMBIO PREFIERES NO MOSTRARLO, DESCOMENTA LA SIGUIENTE LÍNEA Y BORRA LO DE ARRIBA:
                            # continue

                        # 4. Curso aprobado con fecha válida
                        else:
                            dt = pd.to_datetime(valor, errors="coerce", dayfirst=True)
                            fecha_fmt = dt.strftime("%d/%m/%Y") if pd.notna(dt) else str(valor).split()[0]
                            capacitaciones.append({
                                "curso": curso,
                                "fecha": fecha_fmt,
                                "estado": "VIGENTE / APROBADO",
                                "clase": "tag-vigente",
                                "origen": sheet
                            })
            except Exception as e_hoja:
                print(f"Error procesando hoja {sheet}: {e_hoja}")
                continue

        # Orden de prioridad: 1° Vigentes, 2° Pendientes, 3° No Aplica
        orden_estados = {"VIGENTE / APROBADO": 0, "PENDIENTE": 1, "NO APLICA": 2}
        capacitaciones.sort(key=lambda x: (orden_estados.get(x["estado"], 3), x["curso"]))
        return capacitaciones

    except Exception as e:
        print(f"Error general en capacitaciones: {e}")
        return []

# ========================================================
# RUTAS DE FLASK
# ========================================================
@app.route("/")
def home():
    error = request.args.get("error")
    datos_emo = []
    datos_cap = []

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
