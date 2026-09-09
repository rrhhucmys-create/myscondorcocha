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

# Enlace directo de descarga de SharePoint
SHAREPOINT_EMO_URL = "https://myscia-my.sharepoint.com/:x:/g/personal/medico_mys_myssa_com_pe/IQAPaufD2Sy1S6VVCVNoI8gHAcMPjChMQ1ZoNfBLDhomzUo?e=hhqbbW&download=1"

# Sincronización de usuarios al arrancar
try:
    sincronizar_usuarios_desde_xlsb()
except Exception as e:
    print(f"Aviso al iniciar base de datos: {e}")

def obtener_datos_emo(dni_usuario):
    """Descarga el Excel de SharePoint y busca TODOS los exámenes del DNI."""
    try:
        headers = {"User-Agent": "Mozilla/3.0"}
        resp = requests.get(SHAREPOINT_EMO_URL, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"No se pudo descargar de SharePoint. Status: {resp.status_code}")
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

        # Normalizar DNI
        df[col_dni] = df[col_dni].astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(8)

        # Filtrar todos los registros de la persona
        registros = df[df[col_dni] == str(dni_usuario).zfill(8)].copy()

        if registros.empty:
            return []

        # Ordenar por fecha EMO de más reciente a más antiguo
        registros["EMO_DT"] = pd.to_datetime(registros[col_emo], errors="coerce", dayfirst=True)
        registros = registros.sort_values(by="EMO_DT", ascending=False)

        def formatear_fecha(valor):
            if pd.isna(valor) or str(valor).strip() == "":
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

        return examenes  # Retorna lista con 1, 2 o más exámenes

    except Exception as e:
        print(f"Error consultando SharePoint EMO: {e}")
        return []

@app.route("/")
def home():
    error = request.args.get("error")
    datos_emo = None

    # Si hay una sesión activa, consultar sus datos médicos
    if session.get("user_dni"):
        datos_emo = obtener_datos_emo(session.get("user_dni"))

    return render_template("index.html", error=error, emo=datos_emo)

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
