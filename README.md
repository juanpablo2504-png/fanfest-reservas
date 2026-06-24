# Reservas Fan Fest 🎫

App en Streamlit para reservar boletos diarios por área, con reglas
ajustables y un dashboard de ocupación.

## Cómo correrla

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abrirá en `http://localhost:8501`.

## Estructura

- **Reservar**: cualquier persona elige área, fecha y cantidad de boletos.
  Las reglas (anticipación, límite por reserva) se aplican automáticamente.
- **Dashboard**: gráficas de ocupación por día y área, con descarga en CSV.
- **Administración** (protegida con contraseña): ajustar reglas, crear/editar
  áreas y su capacidad, y cancelar reservas.
  - Contraseña por defecto: `admin123` — cámbiala en la pestaña **Seguridad**
    apenas la uses por primera vez.

## Datos

Todo se guarda en un archivo local `reservas.db` (SQLite) que se crea solo
la primera vez que corres la app. Por defecto vienen 3 áreas configuradas
que suman 70 boletos/día (General: 40, VIP: 10, Staff/Prensa: 20) — ajusta
esos nombres y capacidades desde Administración → Áreas.

## Nota sobre despliegue

Si la subes a un servicio como Streamlit Community Cloud, ten en cuenta que
el archivo `reservas.db` puede reiniciarse si la app se redespliega o
duerme por inactividad. Para uso en producción con muchos usuarios
simultáneos, conviene migrar a una base de datos externa (por ejemplo
Postgres/Supabase) — el código está organizado para que ese cambio solo
toque las funciones de la sección "BASE DE DATOS".
