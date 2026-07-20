import streamlit as st
from supabase import create_client
from datetime import datetime, date, time, timedelta

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

# Gerenciamento de sessão
if "user" not in st.session_state:
    st.session_state.user = None

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

# ATUALIZADO: Função para enviar e-mail de resgate de senha
def recuperar_senha(email):
    try:
        supabase.auth.reset_password_email(email)
        st.success("📩 E-mail de recuperação enviado! Verifique sua caixa de entrada e a pasta de Spam/Lixo Eletrônico.")
    except Exception as e:
        st.error(f"Erro ao enviar resgate: {e}")

# ATUALIZADO: Função para alterar a senha com o usuário logado
def atualizar_senha(nova_senha):
    try:
        supabase.auth.update_user({"password": nova_senha})
        st.success("🔒 Senha atualizada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao atualizar senha: {e}")

# ==========================================
# FUNÇÃO DE VALIDAÇÃO DE CONFLITO
# ==========================================
def verificar_conflito(dt_inicio, dt_fim, ignore_id=None):
    query = supabase.table("agendamentos").select("*")\
        .lt("data_inicio", dt_fim)\
        .gt("data_fim", dt_inicio)
        
    if ignore_id:
        query = query.neq("id", ignore_id)
        
    res = query.execute()
    return res.data

# ==========================================
# INTERFACE DE LOGIN / CADASTRO / RESGATE
# ==========================================
if not st.session_state.user:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 Portal do Auditório")
        st.write("Faça login para gerenciar e reservar horários.")
        
        # ATUALIZADO: Adicionada a aba "Esqueci a Senha"
        tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Cadastrar", "❓ Esqueci a Senha"])
        
        with tab1:
            email = st.text_input("E-mail", key="login_email")
            password = st.text_input("Senha", type="password", key="login_pass")
            if st.button("Entrar", use_container_width=True, type="primary"):
                login(email, password)
                
        with tab2:
            col_nome, col_sobre = st.columns(2)
            with col_nome:
                new_nome = st.text_input("Nome", key="signup_nome")
            with col_sobre:
                new_sobrenome = st.text_input("Sobrenome", key="signup_sobrenome")
                
            new_email = st.text_input("E-mail", key="signup_email")
            new_password = st.text_input("Senha", type="password", key="signup_pass")
            
            if st.button("Cadastrar", use_container_width=True):
                if not new_nome or not new_sobrenome:
                    st.warning("⚠️ Por favor, preencha seu nome e sobrenome.")
                elif not new_email or not new_password:
                    st.warning("⚠️ Preencha o e-mail e a senha.")
                else:
                    signup(new_email, new_password, new_nome, new_sobrenome)
                    
        with tab3:
            st.markdown("### Resgatar Acesso")
            st.write("Digite o e-mail cadastrado. Enviaremos um link de autenticação seguro para você poder entrar e escolher uma nova senha.")
            rec_email = st.text_input("E-mail da sua conta", key="rec_email")
            if st.button("Enviar link de resgate", use_container_width=True):
                if not rec_email:
                    st.warning("⚠️ Digite um e-mail válido para receber o link.")
                else:
                    recuperar_senha(rec_email)

# ==========================================
# ÁREA LOGADA - SISTEMA DE AGENDAMENTO
# ==========================================
else:
    meta = st.session_state.user.user_metadata or {}
    nome_usuario = meta.get("nome", "")
    sobrenome_usuario = meta.get("sobrenome", "")
    
    if nome_usuario and sobrenome_usuario:
        nome_exibicao = f"{nome_usuario} {sobrenome_usuario}"
    else:
        nome_exibicao = st.session_state.user.email

    st.sidebar.title("🏢 Auditório")
    st.sidebar.markdown(f"**Usuário:**\n### 👤 {nome_exibicao}")
    st.sidebar.caption(f"E-mail de login: `{st.session_state.user.email}`")
    
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.divider()
    
    # ==========================================
    # ATUALIZADO: Painel de Troca de Senha na Sidebar
    # ==========================================
    with st.sidebar.expander("🔒 Alterar Minha Senha"):
        with st.form("form_mudar_senha", clear_on_submit=True):
            nova_senha = st.text_input("Nova Senha", type="password")
            conf_senha = st.text_input("Confirme a Nova Senha", type="password")
            
            if st.form_submit_button("Salvar Nova Senha", use_container_width=True):
                if not nova_senha or len(nova_senha) < 6:
                    st.warning("⚠️ A senha deve ter pelo menos 6 caracteres.")
                elif nova_senha != conf_senha:
                    st.error("⚠️ As senhas digitadas não coincidem!")
                else:
                    atualizar_senha(nova_senha)
                    
    st.sidebar.divider()
    st.sidebar.subheader("🔍 Filtros de Visualização")
    
    filtro_periodo = st.sidebar.radio(
        "Período:",
        ["Apenas Hoje", "Próximos 7 dias", "A partir de Hoje (Futuros)", "Todos (Incluindo Passados)"],
        index=2
    )
    
    filtro_busca = st.sidebar.text_input("🔎 Buscar por título ou assunto:")
    
    # ------------------------------------------
    # BUSCA DE DADOS NO BANCO
    # ------------------------------------------
    res = supabase.table("agendamentos").select("*").order("data_inicio").execute()
    todos_eventos = res.data if res.data else []
    
    # ------------------------------------------
    # CÁLCULO DE MÉTRICAS (TOPO)
    # ------------------------------------------
    hoje = date.today()
    eventos_hoje = 0
    meus_eventos = 0
    eventos_futuros = 0
    
    for ev in todos_eventos:
        dt_ini = datetime.fromisoformat(ev["data_inicio"])
        if dt_ini.date() == hoje:
            eventos_hoje += 1
        if dt_ini.date() >= hoje:
            eventos_futuros += 1
        if ev["user_id"] == st.session_state.user.id and dt_ini.date() >= hoje:
            meus_eventos += 1

    st.title("📅 Painel de Reservas do Auditório")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("📍 Reuniões Hoje", eventos_hoje)
    m2.metric("🗓️ Total Agendado (Futuro)", eventos_futuros)
    m3.metric("👤 Minhas Reservas Ativas", meus_eventos)
    
    st.markdown("---")

    col_form, col_lista = st.columns([1, 2])

    # ------------------------------------------
    # COLUNA 1: FORMULÁRIO DE NOVO AGENDAMENTO
    # ------------------------------------------
    with col_form:
        st.subheader("➕ Nova Reserva")
        with st.container(border=True):
            with st.form("form_agendamento", clear_on_submit=True):
                titulo = st.text_input("Título / Assunto", placeholder="Ex: Reunião Comercial")
                data_evento = st.date_input("Data", min_value=hoje)
                
                c_ini, c_fim = st.columns(2)
                with c_ini:
                    hora_inicio = st.time_input("Início", value=time(9, 0))
                with c_fim:
                    hora_fim = st.time_input("Término", value=time(10, 0))
                
                submit = st.form_submit_button("Agendar Auditório", use_container_width=True, type="primary")
                
                if submit:
                    if not titulo:
                        st.warning("Por favor, informe o título do evento.")
                    elif hora_inicio >= hora_fim:
                        st.error("O término deve ser posterior ao início.")
                    else:
                        dt_inicio = datetime.combine(data_evento, hora_inicio).isoformat()
                        dt_fim = datetime.combine(data_evento, hora_fim).isoformat()
                        
                        conflitos = verificar_conflito(dt_inicio, dt_fim)
                        
                        if conflitos:
                            st.error(f"⚠️ Conflito! Já reservado para: **{conflitos[0]['titulo']}** neste período.")
                        else:
                            try:
                                supabase.table("agendamentos").insert({
                                    "titulo": titulo,
                                    "data_inicio": dt_inicio,
                                    "data_fim": dt_fim,
                                    "user_id": st.session_state.user.id
                                }).execute()
                                st.success("🎉 Reservado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")

    # ------------------------------------------
    # COLUNA 2: LISTA DE AGENDAMENTOS COM FILTROS
    # ------------------------------------------
    with col_lista:
        st.subheader("📋 Agenda de Eventos")
        
        eventos_filtrados = []
        for ev in todos_eventos:
            dt_ini = datetime.fromisoformat(ev["data_inicio"])
            
            if filtro_busca and filtro_busca.lower() not in ev["titulo"].lower():
                continue
                
            if filtro_periodo == "Apenas Hoje" and dt_ini.date() != hoje:
                continue
            elif filtro_periodo == "Próximos 7 dias" and not (hoje <= dt_ini.date() <= hoje + timedelta(days=7)):
                continue
            elif filtro_periodo == "A partir de Hoje (Futuros)" and dt_ini.date() < hoje:
                continue
                
            eventos_filtrados.append(ev)
        
        if not eventos_filtrados:
            st.info("Nenhum agendamento encontrado para o filtro selecionado.")
        else:
            for ev in eventos_filtrados:
                dt_ini_obj = datetime.fromisoformat(ev["data_inicio"])
                dt_fim_obj = datetime.fromisoformat(ev["data_fim"])
                
                data_str = dt_ini_obj.strftime("%d/%m/%Y")
                hora_ini_str = dt_ini_obj.strftime("%H:%M")
                hora_fim_str = dt_fim_obj.strftime("%H:%M")
                
                is_meu_evento = ev["user_id"] == st.session_state.user.id
                card_style = "🥇 **[Minha Reserva]** " if is_meu_evento else "📌 "
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    with c1:
                        st.markdown(f"{card_style}**{ev['titulo']}**")
                    with c2:
                        st.markdown(f"🕒 `{data_str}` | **{hora_ini_str} às {hora_fim_str}**")
                    with c3:
                        if is_meu_evento:
                            if st.button("❌ Cancelar", key=f"del_{ev['id']}", use_container_width=True):
                                supabase.table("agendamentos").delete().eq("id", ev["id"]).execute()
                                st.rerun()
                    
                    if is_meu_evento:
                        with st.expander("✏️ Editar reserva"):
                            with st.form(key=f"edit_form_{ev['id']}"):
                                new_title = st.text_input("Título", value=ev["titulo"])
                                new_date = st.date_input("Data", value=dt_ini_obj.date(), min_value=hoje)
                                
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    new_start = st.time_input("Início", value=dt_ini_obj.time())
                                with ec2:
                                    new_end = st.time_input("Término", value=dt_fim_obj.time())
                                
                                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                                    if not new_title:
                                        st.warning("O título não pode ficar em branco.")
                                    elif new_start >= new_end:
                                        st.error("O término deve ser posterior ao início.")
                                    else:
                                        new_dt_ini = datetime.combine(new_date, new_start).isoformat()
                                        new_dt_fim = datetime.combine(new_date, new_end).isoformat()
                                        
                                        conflitos = verificar_conflito(new_dt_ini, new_dt_fim, ignore_id=ev["id"])
                                        if conflitos:
                                            st.error(f"⚠️ Conflito com: **{conflitos[0]['titulo']}**.")
                                        else:
                                            supabase.table("agendamentos").update({
                                                "titulo": new_title,
                                                "data_inicio": new_dt_ini,
                                                "data_fim": new_dt_fim
                                            }).eq("id", ev["id"]).execute()
                                            st.success("Atualizado!")
                                            st.rerun()
