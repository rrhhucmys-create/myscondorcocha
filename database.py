import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

ARCHIVO_XLSB = "TAREO SEMANA 2 (version 1).xlsb"
DB_NAME = "usuarios_mys.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def sincronizar_usuarios_desde_xlsb():
    """Lee el archivo binario XLSB, genera credenciales y puebla SQLite."""
    print("Leyendo hoja 'LISTA' del archivo XLSB...")
    
    # Leemos la hoja LISTA usando el motor pyxlsb
    df = pd.read_excel(ARCHIVO_XLSB, sheet_name="LISTA", engine="pyxlsb")
    
    # Limpieza de nombres de columnas (quitar espacios en blanco)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Validar que existan las columnas requeridas
    if "DNI" not in df.columns or "NOMBRE" not in df.columns:
        raise ValueError("No se encontraron las columnas 'DNI' y 'NOMBRE' en la hoja LISTA.")
    
    # Filtrar filas vacías
    df = df.dropna(subset=["DNI", "NOMBRE"])
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Crear la tabla de usuarios
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
    
    registros_insertados = 0
    
    for _, row in df.iterrows():
        dni_raw = str(row["DNI"]).strip()
        
        # Si el DNI viene como float (ej. 72110830.0), lo convertimos a entero limpio
        if dni_raw.endswith(".0"):
            dni = dni_raw[:-2].zfill(8)
        else:
            dni = dni_raw.zfill(8)
            
        nombre_completo = str(row["NOMBRE"]).strip()
        if not dni or not nombre_completo or dni == "00000000":
            continue
            
        # Extraer primera palabra del nombre (en mayúsculas)
        primera_palabra = nombre_completo.split()[0].upper()
        
        # Generar contraseña: PRIMERAPALABRA + DNI (ej: JORGE72110830)
        password_plana = f"{primera_palabra}{dni}"
        password_hash = generate_password_hash(password_plana)
        
        cargo = str(row.get("CARGO", "")).strip() if pd.notna(row.get("CARGO")) else ""
        area = str(row.get("LINEA", "")).strip() if pd.notna(row.get("LINEA")) else ""
        
        # Insertar o actualizar
        cursor.execute("""
            INSERT OR REPLACE INTO usuarios (dni, password_hash, nombre_completo, cargo, area)
            VALUES (?, ?, ?, ?, ?)
        """, (dni, password_hash, nombre_completo, cargo, area))
        
        registros_insertados += 1

    conn.commit()
    conn.close()
    print(f"¡Sincronización exitosa! Se cargaron {registros_insertados} usuarios en SQLite.")

if __name__ == "__main__":
    sincronizar_usuarios_desde_xlsb()
