import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

# Importamos la función de sincronización de database.py
from database import DB_NAME, get_connection, sincronizar_usuarios_desde_xlsb

app = Flask(__name__)
app.secret_key = "myssa_clave_secreta_tareo_2026"

# Si la base de datos aún no existe en el servidor, se crea desde el XLSB al arrancar
if not os.path.exists(DB_NAME):
    try:
        sincronizar_usuarios_desde_xlsb()
    except Exception as e:
        print(f"Advertencia al inicializar base de datos: {e}")

@app.route("/")
def home():
    error = request.args.get("error")
    return render_template("index.html", error=error)

@app.route("/login", methods=["POST"])
def login():
    dni_input = request.form.get("username", "").strip()
    password_input = request.form.get("password", "").strip()
    
    # Asegurar formato de 8 dígitos si ingresó DNI numérico
    if dni_input.isdigit() and len(dni_input) < 8:
        dni_input = dni_input.zfill(8)
    
    conn = get_connection()
    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE dni = ?", (dni_input,)
    ).fetchone()
    conn.close()
    
    if usuario and check_password_hash(usuario["password_hash"], password_input):
        # Guardar en sesión
        session["user_dni"] = usuario["dni"]
        session["nombre_completo"] = usuario["nombre_completo"]
        session["cargo"] = usuario["cargo"]
        return redirect(url_for("home"))
    else:
        return redirect(url_for("home", error="DNI o contraseña incorrectos. Recuerde: contraseña = PRIMER_NOMBRE + DNI"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
