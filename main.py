import streamlit as st
from supabase import create_client
from datetime import datetime, date, time, timedelta
import calendar

# Configuração da página
st.set_page_config(
    page_title="Agendamento Auditório", 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Inicialização de variáveis de sessão
if "user" not in st.session_state: st.session_state.user = None
if "data_reserva" not in st.session_state: st.session_state.data_reserva = date.today()
if "cal_mes" not in st.session_state: st.session_state.cal_mes = date.today().month
if "cal_ano" not in st.session_state: st.session_state.cal_ano = date.today().year
if "input_titulo" not in st.session_state: st.session_state.input_titulo = ""

# Funções de Auth e Lógica
def login(email, password):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user.user
        st.rerun()
    except Exception as e: st.error(f"Erro no login: {e}")

def signup(email, password, nome, sobrenome):
    try:
        supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"nome": nome, "sobrenome": sobrenome}}})
        st.success("Cadastro realizado! Vá em 'Entrar'.")
    except Exception as e: st.error(f"Erro: {e}")

def atualizar_senha(nova_senha):
    try:
        supabase.auth.update_user({"password": nova_senha})
        st.success("Senha atualizada!")
    except Exception as e: st.error(f"Erro: {e}")

def verificar_conflito(dt_inicio, dt_fim, ignore_id=None):
    query = supabase.table("agendamentos").select("*").lt("data_inicio", dt_fim).gt("data_fim", dt_inicio)
    if ignore_id: query = query.neq("id", ignore_id)
    return query.execute().data

def selecionar_data(nova_data):
    if nova_data < date.today(): st.toast("Não é possível agendar no passado!", icon="❌")
    else:
        st.session_state.data_reserva = nova_data
        st.session_state.cal_mes = nova_data.month
        st.session_state.cal_ano = nova_data.year

def sync_calendario():
    st.session_state.cal_mes = st.session_state.data_reserva.month
    st.session_state.cal_ano = st.session_state.data_reserva.year

def renderizar_calendario_interativo(ano, mes, todos_eventos):
    eventos_por_dia = {}
    for ev in todos_eventos:
        dt_ini = datetime.fromisoformat(ev["data_inicio"])
        if dt_ini.year == ano and dt_ini.month == mes:
            dia = dt_ini.day
            if dia not in eventos_por_dia: eventos_por_dia[dia] = []
            eventos_por_dia[dia].append(f"• {ev['titulo']}")

    cols_header = st.columns(7)
    for i, d in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
        cols_header[i].markdown(f"<div style='text-align: center; font-weight: bold;'>{d}</div>", unsafe_allow_html=True)
    
    cal = calendar.monthcalendar(ano, mes)
    for semana in cal:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia != 0:
                dia_data = date(ano, mes, dia)
                emoji = "🔴" if dia in eventos_por_dia else "🟢"
                btn_type = "primary" if dia_data == st.session_state.data_reserva else "secondary"
                cols[i].button(f"{emoji} {dia:02d}", key=f"btn_{ano}_{mes}_{dia}", type=btn_type, use_container_width=True, on_click=selecionar_data, args=(dia_data,))

# ==========================================
# INTERFACE
# ==========================================
if not st.session_state.user:
    st.title("🏢 Portal do Auditório")
    tab1, tab2 = st.tabs(["🔑 Entrar", "📝 Cadastrar"])
    with tab1:
        email = st.text_input("E-mail", key="l_email")
        password = st.text_input("Senha", type="password", key="l_pass")
        if st.button("Entrar"): login(email, password)
    with tab2:
        n = st.text_input("Nome", key="c_nome")
        s = st.text_input("Sobrenome", key="c_sobre")
        e = st.text_input("E-mail", key="c_email")
        p = st.text_input("Senha", type="password", key="c_pass")
        if st.button("Cadastrar"): signup(e, p, n, s)
else:
    # SIDEBAR
    meta = st.session_state.user.user_metadata or {}
    nome_exib = f"{meta.get('nome', '')} {meta.get('sobrenome', '')}"
    st.sidebar.markdown(f"### 👤 {nome_exib_exib if nome_exib != ' ' else st.session_state.user.email}")
    if st.sidebar.button("🚪 Sair"): 
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    
    st.sidebar.divider()
    st.sidebar.subheader("ℹ️ Informações")
    st.sidebar.info("**Auditório Principal**\n📍 Térreo\n👥 Capacidade: 50 pessoas")
    st.sidebar.divider()
    st.sidebar.markdown("""<div style="font-size: 10px; color: #666; text-align: center;">© 2026 GERTAXI. All Rights Reserved.<br>Desenvolvido por ANDRÉ GUIMARÃES</div>""", unsafe_allow_html=True)

    # CORPO
    st.title("📅 Painel de Reservas")
    res = supabase.table("agendamentos").select("*").order("data_inicio").execute()
    todos_eventos = res.data or []
    
    st.subheader("📋 Eventos Agendados")
    with st.container(height=300, border=True):
        for ev in todos_eventos:
            st.write(f"📌 {ev['titulo']} - {datetime.fromisoformat(ev['data_inicio']).strftime('%d/%m/%Y %H:%M')}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("➕ Nova Reserva")
        titulo = st.text_input("Título", key="input_titulo")
        data_res = st.date_input("Data", key="data_reserva", on_change=sync_calendario)
        c1, c2 = st.columns(2)
        hi = c1.time_input("Início", value=time(9,0))
        hf = c2.time_input("Término", value=time(10,0))
        if st.button("Reservar"):
            # Lógica de inserção...
            st.success("Reservado!")
    
    with col2:
        st.subheader("📆 Calendário")
        renderizar_calendario_interativo(st.session_state.cal_ano, st.session_state.cal_mes, todos_eventos)
