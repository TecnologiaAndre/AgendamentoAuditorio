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

# Gerenciamento de sessão e variáveis globais do calendário
if "user" not in st.session_state:
    st.session_state.user = None
if "data_reserva" not in st.session_state:
    st.session_state.data_reserva = date.today()
if "cal_mes" not in st.session_state:
    st.session_state.cal_mes = date.today().month
if "cal_ano" not in st.session_state:
    st.session_state.cal_ano = date.today().year
if "input_titulo" not in st.session_state:
    st.session_state.input_titulo = ""

# ==========================================
# FUNÇÕES DE AUTENTICAÇÃO E SEGURANÇA
# ==========================================
def login(email, password):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user.user
        st.rerun()
    except Exception as e:
        st.error(f"Erro no login: {e}")

def signup(email, password, nome, sobrenome):
    try:
        supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {
                    "nome": nome,
                    "sobrenome": sobrenome
                }
            }
        })
        st.success("🎉 Cadastro realizado com sucesso! Agora vá na aba 'Entrar' e faça seu login.")
    except Exception as e:
        st.error(f"Erro no cadastro: {e}")

def recuperar_senha(email):
    try:
        supabase.auth.reset_password_email(email)
        st.success("📩 E-mail de recuperação enviado! Verifique sua caixa de entrada e a pasta de Spam/Lixo Eletrônico.")
    except Exception as e:
        st.error(f"Erro ao enviar resgate: {e}")

def atualizar_senha(nova_senha):
    try:
        supabase.auth.update_user({"password": nova_senha})
        st.success("🔒 Senha atualizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar senha: {e}")

# ==========================================
# FUNÇÕES DE VALIDAÇÃO E SINCRONIZAÇÃO
# ==========================================
def verificar_conflito(dt_inicio, dt_fim, ignore_id=None):
    query = supabase.table("agendamentos").select("*")\
        .lt("data_inicio", dt_fim)\
        .gt("data_fim", dt_inicio)
        
    if ignore_id:
        query = query.neq("id", ignore_id)
        
    res = query.execute()
    return res.data

def selecionar_data(nova_data):
    if nova_data < date.today():
        st.toast("⚠️ Não é possível agendar em datas passadas!", icon="❌")
    else:
        st.session_state.data_reserva = nova_data
        st.session_state.cal_mes = nova_data.month
        st.session_state.cal_ano = nova_data.year
        st.toast(f"🗓️ Data {nova_data.strftime('%d/%m/%Y')} aplicada no formulário!", icon="🎯")

def sync_calendario():
    st.session_state.cal_mes = st.session_state.data_reserva.month
    st.session_state.cal_ano = st.session_state.data_reserva.year

# ==========================================
# GERADOR DE CALENDÁRIO INTERATIVO
# ==========================================
def renderizar_calendario_interativo(ano, mes, todos_eventos):
    eventos_por_dia = {}
    for ev in todos_eventos:
        dt_ini = datetime.fromisoformat(ev["data_inicio"])
        dt_fim = datetime.fromisoformat(ev["data_fim"])
        if dt_ini.year == ano and dt_ini.month == mes:
            dia = dt_ini.day
            if dia not in eventos_por_dia:
                eventos_por_dia[dia] = []
            h_ini = dt_ini.strftime("%H:%M")
            h_fim = dt_fim.strftime("%H:%M")
            eventos_por_dia[dia].append(f"• {ev['titulo']} ({h_ini} - {h_fim})")

    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    cols_header = st.columns(7)
    for i, d in enumerate(dias_semana):
        cols_header[i].markdown(f"<div style='text-align: center; font-weight: bold; font-size: 14px; color: #888; padding-bottom: 5px;'>{d}</div>", unsafe_allow_html=True)
        
    cal = calendar.monthcalendar(ano, mes)
    hoje = date.today()
    
    for semana in cal:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia == 0:
                cols[i].write("") 
            else:
                dia_data = date(ano, mes, dia)
                is_hoje = (dia_data == hoje)
                is_selecionado = (dia_data == st.session_state.data_reserva)
                
                if dia in eventos_por_dia:
                    emoji = "🔴"
                    detalhes = "\n".join(eventos_por_dia[dia])
                    tooltip = f"📅 RESERVAS NO DIA {dia:02d}:\n{detalhes}\n\n👉 Clique para selecionar esta data"
                else:
                    emoji = "🟢"
                    tooltip = f"Dia {dia:02d} Livre!\n👉 Clique para aplicar no formulário"
                    
                if is_hoje:
                    tooltip = f"[HOJE] {tooltip}"
                
                label = f"{emoji} {dia:02d}"
                btn_type = "primary" if is_selecionado else "secondary"
                
                cols[i].button(
                    label, 
                    key=f"btn_cal_{ano}_{mes}_{dia}", 
                    help=tooltip, 
                    type=btn_type, 
                    use_container_width=True,
                    on_click=selecionar_data,
                    args=(dia_data,)
                )

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
if not st.session_state.user:
    # (Tela de Login mantida igual)
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 Portal do Auditório")
        tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Cadastrar", "❓ Esqueci a Senha"])
        with tab1:
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Entrar", use_container_width=True, type="primary"):
                login(email, password)
        with tab2:
            col_nome, col_sobre = st.columns(2)
            with col_nome: new_nome = st.text_input("Nome", key="signup_nome")
            with col_sobre: new_sobrenome = st.text_input("Sobrenome", key="signup_sobrenome")
            new_email = st.text_input("E-mail", key="signup_email")
            new_password = st.text_input("Senha", type="password", key="signup_pass")
            if st.button("Cadastrar", use_container_width=True):
                if not new_nome or not new_sobrenome: st.warning("⚠️ Preencha nome e sobrenome.")
                elif not new_email or not new_password: st.warning("⚠️ Preencha e-mail e senha.")
                else: signup(new_email, new_password, new_nome, new_sobrenome)
        with tab3:
            rec_email = st.text_input("E-mail da sua conta", key="rec_email")
            if st.button("Enviar link de resgate", use_container_width=True):
                if not rec_email: st.warning("⚠️ Digite um e-mail válido.")
                else: recuperar_senha(rec_email)
else:
    # --- ÁREA LOGADA ---
    meta = st.session_state.user.user_metadata or {}
    nome_exibicao = f"{meta.get('nome', '')} {meta.get('sobrenome', '')}" if meta.get('nome') else st.session_state.user.email

    st.sidebar.title("🏢 Auditório")
    st.sidebar.markdown(f"**Usuário:**\n### 👤 {nome_exibicao}")
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    
    st.sidebar.divider()
    with st.sidebar.expander("🔒 Alterar Minha Senha"):
        with st.form("form_mudar_senha", clear_on_submit=True):
            nova_senha = st.text_input("Nova Senha", type="password")
            conf_senha = st.text_input("Confirme a Nova Senha", type="password")
            if st.form_submit_button("Salvar Nova Senha"):
                if nova_senha != conf_senha: st.error("Senhas não coincidem!")
                else: atualizar_senha(nova_senha)

    st.sidebar.divider()
    st.sidebar.subheader("🔍 Filtros da Agenda")
    filtro_periodo = st.sidebar.radio("Período de visualização:", ["Apenas Hoje", "Próximos 7 dias", "A partir de Hoje (Futuros)", "Todos (Incluindo Passados)"], index=2)
    filtro_busca = st.sidebar.text_input("🔎 Buscar por título ou assunto:")

    # --- NOVO BLOCO SIDEBAR SOLICITADO ---
    st.sidebar.divider()
    st.sidebar.subheader("ℹ️ Informações")
    st.sidebar.info("**Auditório Principal**\n📍 Térreo\n👥 Capacidade: 50 pessoas\n💻 Projetor e Som")
    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div style="font-size: 10px; color: #666; text-align: center;">
            © 2026 GERTAXI. All Rights Reserved.<br>
            Desenvolvido por ANDRÉ GUIMARÃES
        </div>
        """, unsafe_allow_html=True
    )

    # --- PAINEL PRINCIPAL ---
    res = supabase.table("agendamentos").select("*").order("data_inicio").execute()
    todos_eventos = res.data if res.data else []
    
    st.title("📅 Painel de Reservas do Auditório")
    # ... (Restante do código de exibição dos eventos e formulário permanece o mesmo)
