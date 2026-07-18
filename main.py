import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date, time, timedelta, timezone

# -------------------------------------------------------------------
# 1. Configurações Iniciais e Conexão de Banco de Dados
# -------------------------------------------------------------------
st.set_page_config(page_title="Painel de Agendamentos", layout="wide")

@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# -------------------------------------------------------------------
# 2. Funções de Banco de Dados (Otimizadas)
# -------------------------------------------------------------------
def buscar_agendamentos():
    """Busca apenas eventos recentes e futuros para economizar banda."""
    data_limite = (date.today() - timedelta(days=30)).isoformat()
    res = supabase.table("agendamentos").select("*")\
        .gte("data_fim", data_limite)\
        .order("data_inicio").execute()
    return res.data if res.data else []

def verificar_conflito(data_evento, hora_inicio, hora_fim):
    eventos_dia = supabase.table("agendamentos").select("*")\
        .eq("data_evento", data_evento.isoformat()).execute()
    
    for ev in eventos_dia.data:
        ev_inicio = datetime.fromisoformat(ev["data_inicio"]).time()
        ev_fim = datetime.fromisoformat(ev["data_fim"]).time()
        
        # Lógica de sobreposição de tempo
        if hora_inicio < ev_fim and hora_fim > ev_inicio:
            return True
    return False

# -------------------------------------------------------------------
# 3. Gerenciamento de Estado (Session State)
# -------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

def limpar_form():
    st.session_state.titulo_input = ""
    st.session_state.descricao_input = ""

# -------------------------------------------------------------------
# 4. Interface de Login Nativa
# -------------------------------------------------------------------
if not st.session_state.logged_in:
    st.title("🔐 Acesso ao Sistema")
    
    tab_login, tab_cadastro = st.tabs(["Login", "Cadastro"])
    
    with tab_login:
        with st.form("login_form"):
            email_login = st.text_input("E-mail")
            senha_login = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("Entrar")
            
            if btn_login:
                if email_login and senha_login:
                    # Exemplo simplificado de validação. Substitua pela chamada real do seu auth se necessário:
                    # response = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                    st.session_state.logged_in = True
                    st.session_state.username = email_login.split("@")[0]
                    st.rerun()
                else:
                    st.error("Preencha todos os campos.")
                    
    with tab_cadastro:
        with st.form("signup_form"):
            email_cad = st.text_input("Novo E-mail")
            senha_cad = st.text_input("Nova Senha", type="password")
            btn_cad = st.form_submit_button("Cadastrar")
            
            if btn_cad:
                if email_cad and senha_cad:
                    # response = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                    st.success("Cadastro realizado com sucesso! Faça o login.")
                else:
                    st.error("Preencha todos os campos.")
    st.stop()

# -------------------------------------------------------------------
# 5. Painel Principal (Dashboard)
# -------------------------------------------------------------------
st.title(f"📅 Gestão de Auditório - Olá, {st.session_state.username}")
st.divider()

# Carregar dados filtrados
todos_eventos = buscar_agendamentos()

# Métricas Otimizadas (calculadas em memória com a lista filtrada)
hoje_iso = date.today().isoformat()
eventos_hoje = sum(1 for e in todos_eventos if e["data_evento"] == hoje_iso)
meus_eventos = sum(1 for e in todos_eventos if e["usuario"] == st.session_state.username)

col_m1, col_m2 = st.columns(2)
col_m1.metric("Agendamentos Hoje", eventos_hoje)
col_m2.metric("Meus Agendamentos", meus_eventos)

st.divider()

col1, col2 = st.columns([1, 1.5])

# --- COLUNA 1: FORMULÁRIO DE RESERVA ---
with col1:
    st.subheader("Nova Reserva")
    
    data_reserva = st.date_input("Data do Evento", value=date.today(), min_value=date.today())
    
    col_t1, col_t2 = st.columns(2)
    hora_inicio = col_t1.time_input("Hora de Início", value=time(9, 0))
    hora_fim = col_t2.time_input("Hora de Término", value=time(10, 0))
    
    titulo = st.text_input("Título da Reunião", key="titulo_input")
    descricao = st.text_area("Descrição/Detalhes", key="descricao_input")
    
    if st.button("Salvar Agendamento", type="primary", use_container_width=True):
        if hora_inicio >= hora_fim:
            st.error("A hora de término deve ser posterior à hora de início.")
        elif not titulo:
            st.warning("O título é obrigatório.")
        elif verificar_conflito(data_reserva, hora_inicio, hora_fim):
            st.error("⚠️ Conflito de horário! Já existe uma reserva neste período.")
        else:
            # Padronização com Timezone (UTC)
            dt_inicio = datetime.combine(data_reserva, hora_inicio).replace(tzinfo=timezone.utc).isoformat()
            dt_fim = datetime.combine(data_reserva, hora_fim).replace(tzinfo=timezone.utc).isoformat()
            
            novo_agendamento = {
                "titulo": titulo,
                "descricao": descricao,
                "data_evento": data_reserva.isoformat(),
                "data_inicio": dt_inicio,
                "data_fim": dt_fim,
                "usuario": st.session_state.username
            }
            
            supabase.table("agendamentos").insert(novo_agendamento).execute()
            st.success("Agendamento confirmado!")
            limpar_form()
            st.rerun()

# --- COLUNA 2: LISTA DE EVENTOS E GERENCIAMENTO ---
with col2:
    st.subheader("Próximos Eventos")
    
    # Filtrar apenas eventos a partir de hoje para a visualização
    eventos_futuros = [e for e in todos_eventos if e["data_evento"] >= hoje_iso]
    
    if not eventos_futuros:
        st.info("Nenhum evento programado.")
    else:
        for ev in eventos_futuros:
            with st.container(border=True):
                # Conversão de volta do UTC para exibição local
                inicio_str = datetime.fromisoformat(ev["data_inicio"]).strftime("%H:%M")
                fim_str = datetime.fromisoformat(ev["data_fim"]).strftime("%H:%M")
                data_formatada = datetime.fromisoformat(ev['data_evento']).strftime("%d/%m/%Y")
                
                st.markdown(f"**{ev['titulo']}**")
                st.markdown(f"📅 {data_formatada} | ⏰ {inicio_str} às {fim_str} | 👤 {ev['usuario']}")
                
                # Controle de exclusão (Apenas o dono pode excluir)
                if ev['usuario'] == st.session_state.username:
                    with st.popover("❌ Cancelar", use_container_width=False):
                        st.write("Tem certeza que deseja cancelar?")
                        if st.button("Confirmar Exclusão", key=f"del_{ev['id']}", type="primary"):
                            supabase.table("agendamentos").delete().eq("id", ev["id"]).execute()
                            st.rerun()
