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
    """Lee el archivo .xlsb disponible y reconstruye la base de datos SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Crear tabla si no existe
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

    # 2. Buscar cualquier archivo .xlsb disponible en la raíz del proyecto
    archivos = glob.glob("*.xlsb")
    if not archivos:
        print("Aviso: No se encontró ningún archivo .xlsb para sincronizar.")
        conn.close()
        return

    # Usar el primer archivo .xlsb encontrado
    archivo_xlsb = archivos[0]
    print(f"Iniciando sincronización desde: {archivo_xlsb}")

    try:
        # 3. Leer la hoja LISTA con el motor binario pyxlsb
        df = pd.read_excel(archivo_xlsb, sheet_name="LISTA", engine="pyxlsb")
        
        # Normalizar encabezados eliminando espacios y pasando a mayúsculas
        df.columns = [str(c).strip().upper() for c in df.columns]

        if "DNI" not in df.columns or "NOMBRE" not in df.columns:
            print("Error: El archivo no contiene las columnas 'DNI' y 'NOMBRE'.")
            conn.close()
            return

        # Descartar filas sin DNI o sin NOMBRE
        df = df.dropna(subset=["DNI", "NOMBRE"])

        # 4. Limpiar datos anteriores para reflejar exactamente el nuevo Excel (altas y bajas)
        cursor.execute("DELETE FROM usuarios")
        conn.commit()

        registros = 0
        for _, row in df.iterrows():
            dni_raw = str(row["DNI"]).strip()
            
            # Limpiar si viene como decimal flotante (ej. 72110830.0)
            if dni_raw.endswith(".0"):
                dni = dni_raw[:-2].zfill(8)
            else:
                dni = dni_raw.zfill(8)

            nombre_completo = str(row["NOMBRE"]).strip()
            
            # Validar que no sea una fila vacía o de relleno
            if not dni or not nombre_completo or dni == "00000000":
                continue

            # Obtener primera palabra en mayúsculas para la contraseña
            primera_palabra = nombre_completo.split()[0].upper()
            
            # Contraseña requerida: PRIMERAPALABRA + DNI (ej. JORGE72110830)
            password_plana = f"{primera_palabra}{dni}"
            password_hash = generate_password_hash(password_plana)

            cargo = str(row.get("CARGO", "")).strip() if pd.notna(row.get("CARGO")) else ""
            area = str(row.get("LINEA", "")).strip() if pd.notna(row.get("LINEA")) else ""

            # Insertar registro seguro
            cursor.execute("""
                INSERT OR REPLACE INTO usuarios (dni, password_hash, nombre_completo, cargo, area)
                VALUES (?, ?, ?, ?, ?)
            """, (dni, password_hash, nombre_completo, cargo, area))
            registros += 1

        conn.commit()
        print(f"¡Sincronización finalizada! {registros} colaboradores actualizados.")
    except Exception as e:
        print(f"Error durante la lectura del archivo .xlsb: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    sincronizar_usuarios_desde_xlsb()
