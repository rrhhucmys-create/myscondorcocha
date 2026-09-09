import os
import glob
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

DB_NAME = "usuarios_mys.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def sincronizar_usuarios_desde_xlsb():
    """Lee el archivo XLSB y crea la base de datos SQLite"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            dni TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            cargo TEXT,
            area TEXT
        )
    """)
    conn.commit()

    # Buscar cualquier archivo .xlsb disponible en la carpeta
    archivos = glob.glob("*.xlsb")
    if not archivos:
        print("No se encontró ningún archivo .xlsb para sincronizar.")
        conn.close()
        return

    archivo_xlsb = archivos[0]
    print(f"Leyendo datos desde: {archivo_xlsb}")

    try:
        # Leer hoja LISTA usando el motor pyxlsb
        df = pd.read_excel(archivo_xlsb, sheet_name="LISTA", engine="pyxlsb")
        
        # Limpiar y normalizar encabezados
        df.columns = [str(c).strip().upper() for c in df.columns]

        # Validar columnas
        if "DNI" in df.columns and "NOMBRE" in df.columns:
            df = df.dropna(subset=["DNI", "NOMBRE"])

            for _, row in df.iterrows():
                dni_raw = str(row["DNI"]).strip()
                if dni_raw.endswith(".0"):
                    dni = dni_raw[:-2].zfill(8)
                else:
                    dni = dni_raw.zfill(8)

                nombre_completo = str(row["NOMBRE"]).strip()
                if not dni or not nombre_completo or dni == "00000000":
                    continue

                # Extraer primera palabra del nombre
                primera_palabra = nombre_completo.split()[0].upper()
                
                # Contraseña: PRIMERAPALABRA + DNI
                password_plana = f"{primera_palabra}{dni}"
                password_hash = generate_password_hash(password_plana)

                cargo = str(row.get("CARGO", "")).strip() if pd.notna(row.get("CARGO")) else ""
                area = str(row.get("LINEA", "")).strip() if pd.notna(row.get("LINEA")) else ""

                cursor.execute("""
                    INSERT OR REPLACE INTO usuarios (dni, password_hash, nombre_completo, cargo, area)
                    VALUES (?, ?, ?, ?, ?)
                """, (dni, password_hash, nombre_completo, cargo, area))

            conn.commit()
            print("Sincronización completada con éxito.")
    except Exception as e:
        print(f"Error procesando XLSB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    sincronizar_usuarios_desde_xlsb()
