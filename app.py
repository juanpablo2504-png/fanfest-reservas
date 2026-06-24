import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta

DB_PATH = "reservas.db"

st.set_page_config(page_title="Reservas Fan Fest", page_icon="🎫", layout="wide")

# ----------------------------------------------------------------------------
# BASE DE DATOS
# ----------------------------------------------------------------------------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS areas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        capacidad_diaria INTEGER NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reglas (
        clave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reservas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        area TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        comentario TEXT,
        creado_en TEXT NOT NULL
    )""")
    conn.commit()

    # Áreas por defecto (suman 70 = el total de boletos diarios)
    c.execute("SELECT COUNT(*) FROM areas")
    if c.fetchone()[0] == 0:
        default_areas = [("General", 40), ("VIP", 10), ("Staff/Prensa", 20)]
        c.executemany("INSERT INTO areas (nombre, capacidad_diaria) VALUES (?,?)", default_areas)

    # Reglas por defecto
    defaults = {
        "max_dias_anticipacion": "4",
        "min_dias_anticipacion": "0",
        "max_boletos_por_reserva": "10",
        "admin_password": "admin123",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO reglas (clave, valor) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()


def get_rule(clave, default=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT valor FROM reglas WHERE clave=?", (clave,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_rule(clave, valor):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO reglas (clave, valor) VALUES (?,?) "
        "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, str(valor)),
    )
    conn.commit()
    conn.close()


def get_areas():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM areas ORDER BY nombre", conn)
    conn.close()
    return df


def add_area(nombre, capacidad):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO areas (nombre, capacidad_diaria) VALUES (?,?)", (nombre, capacidad))
    conn.commit()
    conn.close()


def update_area_capacity(area_id, capacidad):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE areas SET capacidad_diaria=? WHERE id=?", (capacidad, area_id))
    conn.commit()
    conn.close()


def delete_area(area_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM areas WHERE id=?", (area_id,))
    conn.commit()
    conn.close()


def get_reservas(fecha_ini=None, fecha_fin=None, area=None):
    conn = get_conn()
    query = "SELECT * FROM reservas WHERE 1=1"
    params = []
    if fecha_ini:
        query += " AND fecha >= ?"
        params.append(str(fecha_ini))
    if fecha_fin:
        query += " AND fecha <= ?"
        params.append(str(fecha_fin))
    if area:
        query += " AND area = ?"
        params.append(area)
    query += " ORDER BY fecha, area"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def add_reserva(fecha, area, cantidad, comentario):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO reservas (fecha, area, cantidad, comentario, creado_en) VALUES (?,?,?,?,?)",
        (str(fecha), area, cantidad, comentario, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_reserva(reserva_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM reservas WHERE id=?", (reserva_id,))
    conn.commit()
    conn.close()


def reservado_en(fecha, area):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(SUM(cantidad),0) FROM reservas WHERE fecha=? AND area=?",
        (str(fecha), area),
    )
    total = c.fetchone()[0]
    conn.close()
    return total


init_db()

# ----------------------------------------------------------------------------
# NAVEGACIÓN
# ----------------------------------------------------------------------------

st.sidebar.title("🎫 Fan Fest")
pagina = st.sidebar.radio("Ir a:", ["Reservar", "Dashboard", "Administración"])

# ----------------------------------------------------------------------------
# PÁGINA: RESERVAR
# ----------------------------------------------------------------------------

if pagina == "Reservar":
    st.title("🎫 Reservar boletos")

    areas_df = get_areas()
    if areas_df.empty:
        st.warning("Todavía no hay áreas configuradas. Ve a Administración para crear una.")
        st.stop()

    max_dias = int(get_rule("max_dias_anticipacion", 4))
    min_dias = int(get_rule("min_dias_anticipacion", 0))
    max_por_reserva = int(get_rule("max_boletos_por_reserva", 10))

    hoy = date.today()
    fecha_min = hoy + timedelta(days=min_dias)
    fecha_max = hoy + timedelta(days=max_dias)

    st.caption(
        f"📌 Reglas activas: puedes reservar entre {fecha_min.strftime('%d/%b')} y "
        f"{fecha_max.strftime('%d/%b')} · máximo {max_por_reserva} boletos por reserva."
    )

    col1, col2 = st.columns(2)
    with col1:
        area_sel = st.selectbox("Área", areas_df["nombre"].tolist())
    with col2:
        fecha_sel = st.date_input(
            "Fecha", value=fecha_min, min_value=fecha_min, max_value=fecha_max
        )

    capacidad_area = int(areas_df.loc[areas_df["nombre"] == area_sel, "capacidad_diaria"].iloc[0])
    ya_reservado = reservado_en(fecha_sel, area_sel)
    disponible = max(0, capacidad_area - ya_reservado)

    st.info(f"Disponibles para **{area_sel}** el **{fecha_sel.strftime('%d/%m/%Y')}**: "
            f"**{disponible}** de {capacidad_area}")

    if disponible == 0:
        st.error("No quedan boletos disponibles para esa combinación de área y fecha.")
    else:
        tope = min(disponible, max_por_reserva)
        cantidad = st.number_input("Cantidad de boletos", min_value=1, max_value=tope, value=1, step=1)
        comentario = st.text_input("Nota / responsable (opcional)")

        if st.button("Reservar", type="primary"):
            disponible_actual = max(0, capacidad_area - reservado_en(fecha_sel, area_sel))
            if cantidad > disponible_actual:
                st.error(f"Solo quedan {disponible_actual} boletos disponibles. Intenta con menos.")
            else:
                add_reserva(fecha_sel, area_sel, cantidad, comentario)
                st.success(f"¡Reserva confirmada! {cantidad} boletos en {area_sel} para el {fecha_sel.strftime('%d/%m/%Y')}.")
                st.rerun()

    st.divider()
    st.subheader(f"Disponibilidad para el {fecha_sel.strftime('%d/%m/%Y')}")
    filas = []
    for _, row in areas_df.iterrows():
        reservado = reservado_en(fecha_sel, row["nombre"])
        filas.append({
            "Área": row["nombre"],
            "Capacidad": row["capacidad_diaria"],
            "Reservado": reservado,
            "Disponible": max(0, row["capacidad_diaria"] - reservado),
        })
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

# ----------------------------------------------------------------------------
# PÁGINA: DASHBOARD
# ----------------------------------------------------------------------------

elif pagina == "Dashboard":
    st.title("📊 Dashboard de reservas")

    areas_df = get_areas()
    hoy = date.today()

    col1, col2 = st.columns(2)
    with col1:
        fecha_ini = st.date_input("Desde", value=hoy)
    with col2:
        fecha_fin = st.date_input("Hasta", value=hoy + timedelta(days=7))

    if fecha_ini > fecha_fin:
        st.error("La fecha 'Desde' no puede ser posterior a 'Hasta'.")
        st.stop()

    df = get_reservas(fecha_ini, fecha_fin)

    capacidad_total_dia = int(areas_df["capacidad_diaria"].sum()) if not areas_df.empty else 0
    num_dias = (fecha_fin - fecha_ini).days + 1
    capacidad_total_rango = capacidad_total_dia * num_dias
    total_reservado = int(df["cantidad"].sum()) if not df.empty else 0
    ocupacion = (total_reservado / capacidad_total_rango * 100) if capacidad_total_rango else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Boletos reservados", total_reservado)
    m2.metric("Capacidad del rango", capacidad_total_rango)
    m3.metric("Ocupación", f"{ocupacion:.1f}%")
    m4.metric("# Reservas", len(df))

    if df.empty:
        st.info("No hay reservas en este rango de fechas todavía.")
    else:
        st.subheader("Boletos reservados por día y área")
        fig = px.bar(
            df, x="fecha", y="cantidad", color="area",
            labels={"fecha": "Fecha", "cantidad": "Boletos", "area": "Área"},
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Total por área")
            por_area = df.groupby("area")["cantidad"].sum().reset_index()
            fig2 = px.pie(por_area, names="area", values="cantidad")
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            st.subheader("Total por día")
            por_dia = df.groupby("fecha")["cantidad"].sum().reset_index()
            fig3 = px.bar(por_dia, x="fecha", y="cantidad")
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Detalle de reservas")
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button(
            "⬇️ Descargar CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name=f"reservas_{fecha_ini}_{fecha_fin}.csv",
            mime="text/csv",
        )

# ----------------------------------------------------------------------------
# PÁGINA: ADMINISTRACIÓN
# ----------------------------------------------------------------------------

elif pagina == "Administración":
    st.title("⚙️ Administración")

    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        pwd = st.text_input("Contraseña de administrador", type="password")
        if st.button("Entrar"):
            if pwd == get_rule("admin_password"):
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.caption("Contraseña por defecto: admin123 (cámbiala en la pestaña Seguridad).")
        st.stop()

    tab_reglas, tab_areas, tab_reservas, tab_seguridad = st.tabs(
        ["Reglas", "Áreas", "Reservas", "Seguridad"]
    )

    # --- Reglas ---
    with tab_reglas:
        st.subheader("Reglas de reservación")
        max_dias = st.number_input(
            "Máximo de días de anticipación para reservar",
            min_value=0, value=int(get_rule("max_dias_anticipacion", 4)),
        )
        min_dias = st.number_input(
            "Mínimo de días de anticipación (0 = se puede reservar el mismo día)",
            min_value=0, value=int(get_rule("min_dias_anticipacion", 0)),
        )
        max_por_reserva = st.number_input(
            "Máximo de boletos por reserva",
            min_value=1, value=int(get_rule("max_boletos_por_reserva", 10)),
        )
        if st.button("Guardar reglas", type="primary"):
            set_rule("max_dias_anticipacion", max_dias)
            set_rule("min_dias_anticipacion", min_dias)
            set_rule("max_boletos_por_reserva", max_por_reserva)
            st.success("Reglas actualizadas.")

    # --- Áreas ---
    with tab_areas:
        st.subheader("Áreas y capacidad diaria")
        areas_df = get_areas()
        st.dataframe(areas_df[["nombre", "capacidad_diaria"]], hide_index=True, use_container_width=True)
        st.caption(f"Capacidad total diaria actual: **{int(areas_df['capacidad_diaria'].sum())}** boletos")

        st.markdown("**Editar capacidad de un área**")
        if not areas_df.empty:
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                area_edit = st.selectbox("Área", areas_df["nombre"].tolist(), key="edit_area_sel")
            with c2:
                cap_actual = int(areas_df.loc[areas_df["nombre"] == area_edit, "capacidad_diaria"].iloc[0])
                nueva_cap = st.number_input("Nueva capacidad", min_value=0, value=cap_actual, key="edit_area_cap")
            with c3:
                st.write("")
                st.write("")
                if st.button("Actualizar"):
                    area_id = int(areas_df.loc[areas_df["nombre"] == area_edit, "id"].iloc[0])
                    update_area_capacity(area_id, nueva_cap)
                    st.success("Capacidad actualizada.")
                    st.rerun()

        st.markdown("**Agregar nueva área**")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            nueva_area_nombre = st.text_input("Nombre del área", key="new_area_name")
        with c2:
            nueva_area_cap = st.number_input("Capacidad diaria", min_value=0, value=10, key="new_area_cap")
        with c3:
            st.write("")
            st.write("")
            if st.button("Agregar área"):
                if nueva_area_nombre.strip():
                    try:
                        add_area(nueva_area_nombre.strip(), nueva_area_cap)
                        st.success("Área agregada.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe un área con ese nombre.")
                else:
                    st.error("Escribe un nombre para el área.")

        st.markdown("**Eliminar área**")
        if not areas_df.empty:
            c1, c2 = st.columns([3, 1])
            with c1:
                area_del = st.selectbox("Área a eliminar", areas_df["nombre"].tolist(), key="del_area_sel")
            with c2:
                st.write("")
                if st.button("Eliminar", type="secondary"):
                    area_id = int(areas_df.loc[areas_df["nombre"] == area_del, "id"].iloc[0])
                    delete_area(area_id)
                    st.success("Área eliminada.")
                    st.rerun()

    # --- Reservas ---
    with tab_reservas:
        st.subheader("Gestionar reservas")
        areas_df = get_areas()
        c1, c2, c3 = st.columns(3)
        with c1:
            f_ini = st.date_input("Desde", value=date.today(), key="admin_f_ini")
        with c2:
            f_fin = st.date_input("Hasta", value=date.today() + timedelta(days=30), key="admin_f_fin")
        with c3:
            area_filtro = st.selectbox("Área (opcional)", ["Todas"] + areas_df["nombre"].tolist())

        df = get_reservas(f_ini, f_fin, None if area_filtro == "Todas" else area_filtro)
        st.dataframe(df, hide_index=True, use_container_width=True)

        if not df.empty:
            st.markdown("**Cancelar una reserva**")
            c1, c2 = st.columns([3, 1])
            with c1:
                id_cancelar = st.selectbox("ID de la reserva", df["id"].tolist())
            with c2:
                st.write("")
                if st.button("Cancelar reserva", type="secondary"):
                    delete_reserva(int(id_cancelar))
                    st.success("Reserva cancelada.")
                    st.rerun()

    # --- Seguridad ---
    with tab_seguridad:
        st.subheader("Cambiar contraseña de administrador")
        nueva_pwd = st.text_input("Nueva contraseña", type="password")
        if st.button("Actualizar contraseña"):
            if nueva_pwd.strip():
                set_rule("admin_password", nueva_pwd.strip())
                st.success("Contraseña actualizada.")
            else:
                st.error("La contraseña no puede estar vacía.")

        st.divider()
        if st.button("Cerrar sesión de administrador"):
            st.session_state.is_admin = False
            st.rerun()
