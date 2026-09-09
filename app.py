from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M&S - Mantenimiento y Supervisión</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #134e5e;
            --primary-dark: #0a2730;
            --secondary: #206377;
            --accent: #38a3a5;
            --bg-light: #f8fafc;
            --card-bg: #ffffff;
            --text-dark: #1e293b;
            --text-muted: #64748b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-light);
            color: var(--text-dark);
            line-height: 1.6;
        }

        /* Barra de navegación */
        header {
            background: #ffffff;
            border-bottom: 2px solid #e2e8f0;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* Isotipo visual M&S */
        .logo-badge {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-family: 'Montserrat', sans-serif;
            font-weight: 800;
            font-size: 1.1rem;
            letter-spacing: -0.5px;
            box-shadow: 0 2px 8px rgba(19, 78, 94, 0.35);
        }

        .brand-text h1 {
            font-family: 'Montserrat', sans-serif;
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary-dark);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            line-height: 1.1;
        }

        .brand-text span {
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* Sección Principal (Hero) */
        .hero {
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
            color: #ffffff;
            padding: 4.5rem 1.5rem;
            text-align: center;
            position: relative;
        }

        .hero::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 12px;
            background: linear-gradient(90deg, var(--accent), #57cc99);
        }

        .hero h2 {
            font-family: 'Montserrat', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 1rem;
            letter-spacing: -0.5px;
        }

        .hero p {
            max-width: 680px;
            margin: 0 auto 1.8rem auto;
            font-size: 1.05rem;
            opacity: 0.92;
            font-weight: 300;
        }

        .badge-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.12);
            backdrop-filter: blur(8px);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #2ecc71;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #2ecc71;
        }

        /* Módulos de Acceso / Tarjetas */
        .container {
            max-width: 1050px;
            margin: -2.5rem auto 3rem auto;
            padding: 0 1rem;
        }

        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
            gap: 1.5rem;
        }

        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 2rem 1.7rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.06), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
            border: 1px solid #e2e8f0;
            border-top: 4px solid var(--primary);
            transition: all 0.25s ease;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 16px 30px -5px rgba(19, 78, 94, 0.15);
            border-top-color: var(--accent);
        }

        .card-icon {
            width: 46px;
            height: 46px;
            background-color: #e0f2f1;
            color: var(--primary);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            margin-bottom: 1.2rem;
        }

        .card h3 {
            font-family: 'Montserrat', sans-serif;
            font-size: 1.2rem;
            color: var(--primary-dark);
            margin-bottom: 0.6rem;
            font-weight: 700;
        }

        .card p {
            color: var(--text-muted);
            font-size: 0.92rem;
            line-height: 1.5;
            margin-bottom: 1.4rem;
        }

        .btn-action {
            display: inline-block;
            background-color: var(--primary);
            color: #ffffff;
            text-decoration: none;
            padding: 0.65rem 1.25rem;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            transition: background-color 0.2s ease;
        }

        .btn-action:hover {
            background-color: var(--primary-dark);
        }

        /* Pie de página */
        footer {
            text-align: center;
            padding: 2rem 1rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            border-top: 1px solid #e2e8f0;
            background-color: #ffffff;
        }
    </style>
</head>
<body>

    <!-- Header Corporativo -->
    <header>
        <div class="brand-container">
            <div class="logo-badge">M&amp;S</div>
            <div class="brand-text">
                <h1>Mantenimiento y Supervisión</h1>
                <span>Portal Operativo &amp; Gestión</span>
            </div>
        </div>
    </header>

    <!-- Banner Principal -->
    <section class="hero">
        <div class="badge-status">
            <span class="pulse-dot"></span> Sistema en línea activo
        </div>
        <h2 style="margin-top: 1.2rem;">Control Operativo &amp; Supervisión</h2>
        <p>Plataforma centralizada para la gestión, registro de tareos, control de horas y automatización de procesos operativos.</p>
    </section>

    <!-- Accesos / Secciones del Sistema -->
    <main class="container">
        <div class="cards-grid">
            <div class="card">
                <div class="card-icon">📋</div>
                <h3>Control de Tareos y Asistencia</h3>
                <p>Carga y procesamiento automático de marcaciones, turnos diurnos/nocturnos y cálculo de horas compensadas.</p>
                <a href="#" class="btn-action">Ingresar al Módulo</a>
            </div>

            <div class="card">
                <div class="card-icon">📊</div>
                <h3>Supervisión &amp; Reportes</h3>
                <p>Consolidación de órdenes de trabajo (OT), métricas operativas y generación de reportes consolidados en Excel.</p>
                <a href="#" class="btn-action">Ver Reportes</a>
            </div>

            <div class="card">
                <div class="card-icon">⚙️</div>
                <h3>Automatización y Datos</h3>
                <p>Herramientas y scripts auxiliares en Python para validación, cruce de información y tareas administrativas.</p>
                <a href="#" class="btn-action">Herramientas</a>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer>
        <p>&copy; 2026 Mantenimiento y Supervisión S.A. &bull; Todos los derechos reservados</p>
    </footer>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
