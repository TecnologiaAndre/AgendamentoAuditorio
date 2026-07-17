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

# Ação executada ao clicar em um dia no calendário da direita
def selecionar_data(nova_data):
    if nova_data < date.today():
        st.toast("⚠️ Não é possível agendar em datas passadas!", icon="❌")
    else:
        st.session_state.data_reserva = nova_data
        st.session_state.cal_mes = nova_data.month
        st.session_state.cal_ano = nova_data.year
        st.toast(f"🗓️ Data {nova_data.strftime('%d/%m/%Y')} aplicada no formulário!", icon="🎯")

# Ação executada ao mudar a data diretamente pelo seletor do formulário
def sync_calendario():
    st.session_state.cal_mes = st.session_state.data_reserva.month
    st.session_state.cal_ano = st.session_state.data_reserva.year

# ==========================================
# GERADOR DE CALENDÁRIO INTERATIVO (GRADE DE BOTÕES)
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
# INTERFACE DE LOGIN / CADASTRO / RESGATE
# ==========================================
if not st.session_state.user:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 Agenda do Auditório")
        st.write("Faça login para gerenciar e reservar horários.")
        
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
    st.sidebar.subheader("🔍 Filtros da Agenda")
    
    filtro_periodo = st.sidebar.radio(
        "Período de visualização:",
        ["Apenas Hoje", "Próximos 7 dias", "A partir de Hoje (Futuros)", "Todos (Incluindo Passados)"],
        index=2
    )
    
    filtro_busca = st.sidebar.text_input("🔎 Buscar por título ou assunto:")
    
    # ------------------------------------------
    # BUSCA DE DADOS NO BANCO
    # ------------------------------------------
    res = supabase.table("agendamentos").select("*").order("data_inicio").execute()
    todos_eventos = res.data if res.data else []

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        <div style="font-size: 12px; color: #E0E0E0; text-align: center; font-weight: bold;">
            © 2026 GERTAXI. All Rights Reserved.<br>
            Desenvolvido por ANDRÉ GUIMARÃES
        </div>
        """,
        unsafe_allow_html=True
    )
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

    # ==========================================================
    # PARTE SUPERIOR: VISUALIZADOR DE EVENTOS
    # ==========================================================
    st.subheader("📋 Agenda de Eventos Agendados")
    st.caption("Confira abaixo os horários já reservados antes de criar uma nova solicitação.")
    
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
    
    with st.container(height=380, border=True):
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
                        with st.expander("✏️ Editar minha reserva"):
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

    st.markdown("---")

    # ==========================================================
    # PARTE INFERIOR: FORMULÁRIO (ESQUERDA) E CALENDÁRIO (DIREITA)
    # ==========================================================
    col_form, col_cal = st.columns([1, 1.3])

    # ------------------------------------------
    # COLUNA ESQUERDA: FORMULÁRIO (AGORA SEM st.form PARA PERMITIR INTERATIVIDADE!)
    # ------------------------------------------
    with col_form:
        st.subheader("➕ Nova Reserva")
        with st.container(border=True):
            titulo = st.text_input(
                "Título / Assunto", 
                placeholder="Ex: Reunião Comercial",
                key="input_titulo"
            )
            
            # Conectado bi-direcionalmente e com callback liberado!
            data_evento = st.date_input(
                "Data da Reserva", 
                key="data_reserva", 
                min_value=hoje, 
                on_change=sync_calendario
            )
            
            c_ini, c_fim = st.columns(2)
            with c_ini:
                hora_inicio = st.time_input("Horário de Início", value=time(9, 0), key="input_ini")
            with c_fim:
                hora_fim = st.time_input("Horário de Término", value=time(10, 0), key="input_fim")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Botão normal (st.button) no lugar do form_submit_button
            if st.button("Aguardar e Reservar Auditório", use_container_width=True, type="primary"):
                if not st.session_state.input_titulo:
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
                                "titulo": st.session_state.input_titulo,
                                "data_inicio": dt_inicio,
                                "data_fim": dt_fim,
                                "user_id": st.session_state.user.id
                            }).execute()
                            st.success("🎉 Auditório reservado com sucesso!")
                            # Limpa o título após salvar a reserva
                            st.session_state.input_titulo = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    # ------------------------------------------
    # COLUNA DIREITA: CALENDÁRIO INTERATIVO DE DISPONIBILIDADE
    # ------------------------------------------
    with col_cal:
        st.subheader("📆 Mapa de Disponibilidade Interativo")
        
        with st.container(border=True):
            cm1, cm2 = st.columns([3, 2])
            meses_nomes = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]
            with cm1:
                st.selectbox(
                    "Mês", 
                    range(1, 13), 
                    format_func=lambda x: meses_nomes[x-1],
                    key="cal_mes"
                )
            with cm2:
                st.selectbox(
                    "Ano", 
                    range(hoje.year - 1, hoje.year + 3), 
                    key="cal_ano"
                )
            
            st.markdown("""
            <div style="font-size: 13px; margin: 5px 0 10px 0; display: flex; gap: 15px; justify-content: center; background: rgba(128,128,128,0.1); padding: 8px; border-radius: 6px;">
                <span>🟢 <b>Livre</b> (Clique)</span>
                <span>🔴 <b>Existe Evento</b> (Passe o mouse)</span>
                <span>🎯 <b>Dia Selecionado</b></span>
            </div>
            """, unsafe_allow_html=True)
            
            renderizar_calendario_interativo(st.session_state.cal_ano, st.session_state.cal_mes, todos_eventos)