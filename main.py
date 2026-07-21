import streamlit as st
from supabase import create_client
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import calendar

# Configuração da página
st.set_page_config(
    page_title="Agendamento Auditório", 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# FUSO HORÁRIO DE REFERÊNCIA (evita depender do horário do servidor)
# =====================================================================
FUSO_LOCAL = ZoneInfo("America/Fortaleza")

def agora_local():
    """Retorna o datetime atual no fuso horário local (Fortaleza/Brasília),
    independente de onde o servidor Streamlit esteja rodando (ex: UTC no Cloud)."""
    return datetime.now(FUSO_LOCAL)

# =====================================================================
# CSS BLINDADO PARA OCULTAR CABEÇALHO, RODAPÉ E BARRA DO STREAMLIT CLOUD
# =====================================================================
st.markdown("""
    <style>
    /* Oculta o cabeçalho padrão, o menu hambúrguer e a marca d'água superior */
    #MainMenu {visibility: hidden !important; display: none !important;}
    header {visibility: hidden !important; display: none !important;}
    header[data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
    
    /* Oculta o rodapé 'Made with Streamlit' */
    footer {visibility: hidden !important; display: none !important;}
    footer[data-testid="stFooter"] {visibility: hidden !important; display: none !important;}
    
    /* Oculta os botões e barras de status flutuantes do Streamlit Cloud (Fullscreen / Running) */
    div[data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    .stApp > header {display: none !important;}
    .stApp > footer {display: none !important;}
    
    /* Ajusta a margem do topo para compensar a remoção do cabeçalho */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Inicialização do Supabase com cache do Streamlit
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# =====================================================================
# CAPTURA DO FRAGMENTO DA URL (#access_token=...) PARA RECOVERY DE SENHA
# =====================================================================
# O Supabase Auth entrega o link de "esqueci a senha" com os tokens depois
# de "#" (fragmento), que NUNCA é enviado ao servidor - só existe no
# navegador. O Streamlit (server-side) não consegue ler isso diretamente
# via st.query_params. Este bloco injeta um JS mínimo que roda uma única
# vez: se detectar "#access_token=" na URL, reescreve a mesma URL movendo
# os dados para query string (?access_token=...) e recarrega a página.
# A partir daí, o Python consegue ler st.query_params normalmente.
if "access_token" not in st.query_params:
    st.markdown(
        """
        <script>
        (function() {
            const hash = window.location.hash;
            if (hash && hash.includes("access_token=")) {
                const params = new URLSearchParams(hash.substring(1));
                const newUrl = window.location.pathname + "?" + params.toString();
                window.location.replace(newUrl);
            }
        })();
        </script>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# GESTÃO DE SESSÃO E ESTADO DO SISTEMA
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None

# Sessão de recuperação de senha ativa (detectada via query params, ver bloco acima)
if "recovery_session" not in st.session_state:
    st.session_state.recovery_session = None

hoje = agora_local().date()

# Define a data padrão para o formulário de reserva caso ainda não exista
if "data_reserva" not in st.session_state:
    st.session_state["data_reserva"] = hoje

# Dicionário no session_state para controlar qual reserva está com a edição aberta
if "editando_reserva_id" not in st.session_state:
    st.session_state["editando_reserva_id"] = None

# Função de Callback: Executa ANTES de redesenhar a tela, evitando erros da API do Streamlit
def selecionar_data_callback(nova_data):
    st.session_state["data_reserva"] = nova_data

# Callback para alternar a abertura/fechamento do painel de edição de um card
def alternar_edicao_callback(reserva_id):
    if st.session_state["editando_reserva_id"] == reserva_id:
        st.session_state["editando_reserva_id"] = None
    else:
        st.session_state["editando_reserva_id"] = reserva_id

# ==========================================
# FUNÇÕES DE AUTENTICAÇÃO E SEGURANÇA
# ==========================================
def login(email, password):
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = user.user
        st.rerun()
    except Exception as e:
        err_msg = str(e)
        if "Invalid login credentials" in err_msg:
            st.error("⚠️ E-mail ou senha incorretos.")
        elif "For security purposes" in err_msg:
            st.error("⏳ Muitas tentativas seguidas. Aguarde alguns segundos e tente novamente.")
        else:
            st.error(f"Erro no login: {err_msg}")

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
        st.success("🎉 Cadastro realizado com sucesso! Agora vá até o seu e-mail e confirme o cadastro!")
    except Exception as e:
        err_msg = str(e)
        if "For security purposes" in err_msg:
            st.error("⏳ Por questões de segurança do servidor, aguarde alguns segundos antes de tentar cadastrar novamente.")
        elif "User already registered" in err_msg:
            st.error("⚠️ Este e-mail já está cadastrado no sistema.")
        else:
            st.error(f"Erro no cadastro: {err_msg}")

def recuperar_senha(email):
    # NOTA: o link de recuperação do Supabase Auth entrega o token no fragmento
    # da URL (#access_token=...), que normalmente é processado por JS no client.
    # Em apps Streamlit "puros" isso pode não ser capturado automaticamente —
    # vale testar esse fluxo ponta a ponta (clicar no link, ver se a sessão de
    # recovery é reconhecida antes de chamar atualizar_senha()).
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

def processar_query_params_recovery():
    """Verifica se a URL trouxe um access_token/refresh_token de recovery
    (já convertidos de fragmento para query string pelo JS acima) e,
    se sim, autentica essa sessão temporária no cliente Supabase para
    permitir a troca de senha."""
    qp = st.query_params
    if "access_token" in qp and qp.get("type") == "recovery":
        try:
            access_token = qp["access_token"]
            refresh_token = qp.get("refresh_token", "")
            session_resp = supabase.auth.set_session(access_token, refresh_token)
            st.session_state.recovery_session = session_resp.session
            # Limpa os parâmetros da URL para não reprocessar / não deixar
            # o token exposto na barra de endereço após o uso.
            st.query_params.clear()
        except Exception as e:
            st.error(f"⚠️ Não foi possível validar o link de recuperação. Ele pode ter expirado ou já ter sido usado. Solicite um novo link. (Detalhe: {e})")

# ==========================================
# FUNÇÃO DE VALIDAÇÃO DE CONFLITO (PRÉ-CHECAGEM)
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
# CALENDÁRIO INTERATIVO NATIVO COM CALLBACK
# ==========================================
def desenhar_calendario_nativo(ano, mes, todos_eventos):
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
    
    st.markdown("""
    <style>
    div[data-testid="column"] { padding: 0px 2px !important; }
    </style>
    """, unsafe_allow_html=True)
    
    cols_header = st.columns(7)
    for idx, d in enumerate(dias_semana):
        cols_header[idx].markdown(f"<div style='text-align: center; font-weight: bold; font-size: 13px; color: gray; margin-bottom: 5px;'>{d}</div>", unsafe_allow_html=True)
        
    cal = calendar.monthcalendar(ano, mes)
    hoje_data = agora_local().date()
    data_selecionada = st.session_state.get("data_reserva", hoje_data)
    
    for semana in cal:
        cols = st.columns(7)
        for idx, dia in enumerate(semana):
            if dia == 0:
                cols[idx].write("")
            else:
                data_celula = date(ano, mes, dia)
                disabled = data_celula < hoje_data
                
                if dia in eventos_por_dia:
                    detalhes = "\n".join(eventos_por_dia[dia])
                    tooltip = f"📅 RESERVAS NO DIA {dia:02d}:\n{detalhes}\n\n👉 Clique para selecionar este dia"
                    icone = "🔴"
                else:
                    tooltip = "Dia Livre - Clique para selecionar esta data"
                    icone = "🟢"
                    
                if data_celula == hoje_data:
                    icone = "🟡"
                    tooltip = f"[HOJE] {tooltip}"
                    
                if data_celula == data_selecionada:
                    icone = "🔵"
                    tooltip = f"[SELECIONADO ATUALMENTE]\n{tooltip}"
                    
                if disabled:
                    icone = "⬛"
                    tooltip = "Data passada (Fechado para agendamentos)"
                
                label = f"{icone} {dia:02d}"
                
                with cols[idx]:
                    st.button(
                        label, 
                        key=f"btn_cal_{ano}_{mes}_{dia}", 
                        help=tooltip, 
                        disabled=disabled, 
                        use_container_width=True,
                        on_click=selecionar_data_callback,
                        args=(data_celula,)
                    )

processar_query_params_recovery()

# ==========================================
# TELA DEDICADA: DEFINIR NOVA SENHA (link de recovery)
# ==========================================
if st.session_state.recovery_session:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Definir Nova Senha")
        st.write("Você chegou aqui através do link de recuperação de senha. Escolha uma nova senha para sua conta.")

        with st.form("form_definir_nova_senha"):
            nova_senha_recovery = st.text_input("Nova Senha", type="password")
            conf_senha_recovery = st.text_input("Confirme a Nova Senha", type="password")
            confirmar_clicado = st.form_submit_button("Salvar Nova Senha", use_container_width=True, type="primary")

        if confirmar_clicado:
            if not nova_senha_recovery or len(nova_senha_recovery) < 6:
                st.warning("⚠️ A senha deve ter pelo menos 6 caracteres.")
            elif nova_senha_recovery != conf_senha_recovery:
                st.error("⚠️ As senhas digitadas não coincidem!")
            else:
                atualizar_senha(nova_senha_recovery)
                st.session_state.recovery_session = None
                st.info("Agora você já pode fazer login normalmente com a nova senha.")
                if st.button("Ir para o login", use_container_width=True):
                    st.rerun()

# ==========================================
# INTERFACE DE LOGIN / CADASTRO / RESGATE
# ==========================================
elif not st.session_state.user:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📅 Agendamento do Auditório")
        st.write("Faça login para gerenciar e reservar horários.")
        
        tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Cadastrar", "❓ Esqueci a Senha"])
        
        with tab1:
            with st.form("form_login"):
                email = st.text_input("E-mail", key="login_email")
                password = st.text_input("Senha", type="password", key="login_pass")
                entrar_clicado = st.form_submit_button("Entrar", use_container_width=True, type="primary")

            if entrar_clicado:
                if not email.strip() or not password.strip():
                    st.warning("⚠️ Preencha o e-mail e a senha.")
                else:
                    login(email.strip(), password)
                
        with tab2:
            with st.form("form_cadastro"):
                col_nome, col_sobre = st.columns(2)
                with col_nome:
                    new_nome = st.text_input("Nome", key="signup_nome")
                with col_sobre:
                    new_sobrenome = st.text_input("Sobrenome", key="signup_sobrenome")

                new_email = st.text_input("E-mail", key="signup_email")
                new_password = st.text_input("Senha", type="password", key="signup_pass")

                cadastrar_clicado = st.form_submit_button("Cadastrar", use_container_width=True)

            if cadastrar_clicado:
                if not new_nome.strip() or not new_sobrenome.strip():
                    st.warning("⚠️ Por favor, preencha seu nome e sobrenome.")
                elif not new_email.strip() or not new_password.strip():
                    st.warning("⚠️ Preencha o e-mail e a senha.")
                elif len(new_password) < 6:
                    st.warning("⚠️ A senha deve ter pelo menos 6 caracteres.")
                else:
                    signup(new_email.strip(), new_password, new_nome.strip(), new_sobrenome.strip())
                    
        with tab3:
            st.markdown("### Resgatar Acesso")
            st.write("Digite o e-mail cadastrado. Enviaremos um link de autenticação seguro para você poder entrar e escolher uma nova senha.")
            with st.form("form_recuperacao"):
                rec_email = st.text_input("E-mail da sua conta", key="rec_email")
                enviar_clicado = st.form_submit_button("Enviar link de resgate", use_container_width=True)

            if enviar_clicado:
                if not rec_email.strip():
                    st.warning("⚠️ Digite um e-mail válido para receber o link.")
                else:
                    recuperar_senha(rec_email.strip())

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

    st.sidebar.title("🎦 Auditório")
    st.sidebar.markdown(f"**Usuário:**\n### 👤 {nome_exibicao}")
    st.sidebar.caption(f"E-mail de login: `{st.session_state.user.email}`")
    
    if st.sidebar.button("SAIR", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
        
    st.sidebar.divider()
    
    with st.sidebar.expander("🔒 Alterar Senha"):
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
    st.sidebar.subheader("🔎 Filtros da Agenda")
    
    filtro_periodo = st.sidebar.radio(
        "Período de visualização:",
        ["Apenas Hoje", "Próximos 7 dias", "A partir de Hoje (Futuros)", "Todos (Incluindo Passados)"],
        index=2
    )
    
    filtro_busca = st.sidebar.text_input("🔎 Buscar por título ou assunto:")
    
    # ------------------------------------------
    # BUSCA OTIMIZADA DE DADOS NO BANCO
    # ------------------------------------------
    # Quando o filtro é "Todos (Incluindo Passados)", buscamos o histórico
    # completo. Nos demais casos, mantemos a otimização de só trazer eventos
    # dos últimos 60 dias pra cá (mais que suficiente para "hoje", "7 dias"
    # e "futuros").
    query_eventos = supabase.table("agendamentos").select("*")
    if filtro_periodo != "Todos (Incluindo Passados)":
        data_limite_query = (hoje - timedelta(days=60)).isoformat()
        query_eventos = query_eventos.gte("data_fim", data_limite_query)

    res = query_eventos.order("data_inicio").execute()
    todos_eventos = res.data if res.data else []
    
    # ------------------------------------------
    # CÁLCULO DE MÉTRICAS (TOPO)
    # ------------------------------------------
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

    # Cabeçalho com o título à esquerda e a assinatura sutil à direita no topo
    col_titulo, col_marca = st.columns([3, 2])
    with col_titulo:
        st.title("📅 Painel de Reservas do Auditório")
    with col_marca:
        st.markdown(
            """
             <div style="text-align: right; font-size: 11.5px; color: gray; padding-top: 18px; font-family: sans-serif;">
                    &copy; 2026 GERTAXI. All Rights Reserved. | Desenvolvido por <br style="display:none;">
                    <a href="https://www.linkedin.com/in/andr3guimara3s/" target="_blank" class="footer-link">ANDRÉ GUIMARÃES</a>
                </div>
            """, 
            unsafe_allow_html=True
        )
    
    m1, m2, m3 = st.columns(3)
    m1.metric("📍 Reuniões Hoje", eventos_hoje)
    m2.metric("🗓️ Total Agendado (Futuro)", eventos_futuros)
    m3.metric("👤 Minhas Reservas Ativas", meus_eventos)
    
    st.markdown("---")

    # ==========================================================
    # PARTE SUPERIOR: FORMULÁRIO (ESQUERDA) E CALENDÁRIO (DIREITA)
    # ==========================================================
    col_form, col_cal = st.columns([1, 1.2])

    with col_form:
        st.subheader("➕ Nova Reserva")
        with st.container(border=True):
            with st.form("form_agendamento", clear_on_submit=True):
                titulo = st.text_input("Título / Assunto", placeholder="Ex: Reunião Comercial")
                
                data_evento = st.date_input("Data da Reserva", min_value=hoje, key="data_reserva")
                
                c_ini, c_fim = st.columns(2)
                with c_ini:
                    hora_inicio = st.time_input("Horário de Início", value=time(9, 0))
                with c_fim:
                    hora_fim = st.time_input("Horário de Término", value=time(10, 0))
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("Aguardar e Reservar Auditório", use_container_width=True, type="primary")
                
                if submit:
                    agora = agora_local()
                    
                    if not titulo.strip():
                        st.warning("Por favor, informe o título do evento.")
                    elif hora_inicio >= hora_fim:
                        st.error("O término deve ser posterior ao início.")
                    elif data_evento == hoje and hora_inicio <= agora.time():
                        st.error("⚠️ Você não pode agendar um horário que já passou hoje!")
                    else:
                        dt_inicio = datetime.combine(data_evento, hora_inicio).isoformat()
                        dt_fim = datetime.combine(data_evento, hora_fim).isoformat()
                        
                        conflitos = verificar_conflito(dt_inicio, dt_fim)
                        
                        if conflitos:
                            st.error(f"⚠️ Conflito! Já reservado para: **{conflitos[0]['titulo']}** neste período.")
                        else:
                            try:
                                supabase.table("agendamentos").insert({
                                    "titulo": titulo.strip(),
                                    "data_inicio": dt_inicio,
                                    "data_fim": dt_fim,
                                    "user_id": st.session_state.user.id
                                }).execute()
                                st.success("🎉 Auditório reservado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                if "evita_sobreposicao_horario" in str(e):
                                    st.error("⚠️ Outro usuário acabou de reservar esse horário uma fração de segundo antes de você! Por favor, escolha outro período no calendário.")
                                else:
                                    st.error(f"Erro ao salvar: {e}")

    with col_cal:
        st.subheader("📆 Mapa de Disponibilidade")
        st.caption("👉 **Dica:** Clique no botão de qualquer dia abaixo para preencher automaticamente a caixinha de Nova Reserva ao lado!")
        
        with st.container(border=True):
            cm1, cm2 = st.columns([3, 2])
            meses_nomes = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]
            
            mes_padrao = st.session_state["data_reserva"].month - 1
            ano_padrao_idx = st.session_state["data_reserva"].year - (hoje.year - 1)
            if ano_padrao_idx < 0 or ano_padrao_idx > 3:
                ano_padrao_idx = 1
                
            with cm1:
                mes_sel = st.selectbox(
                    "Mês", 
                    range(1, 13), 
                    index=mes_padrao, 
                    format_func=lambda x: meses_nomes[x-1]
                )
            with cm2:
                ano_sel = st.selectbox("Ano", range(hoje.year - 1, hoje.year + 3), index=ano_padrao_idx)
            
            st.markdown("""
            <div style="font-size: 13px; margin-bottom: 12px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                <span>🟢 <b>Livre</b></span>
                <span>🔴 <b>Ocupado - Verificar Disponibilidade</b> (Passe o mouse)</span>
                <span>🟡 <b>Hoje</b></span>
                <span>🔵 <b>Selecionado</b></span>
                <span>⬛ <b>Passado</b></span>
            </div>
            """, unsafe_allow_html=True)
            
            desenhar_calendario_nativo(ano_sel, mes_sel, todos_eventos)

    st.markdown("---")

    # ==========================================================
    # PARTE INFERIOR: VISUALIZADOR DE EVENTOS
    # ==========================================================
    st.subheader("📋 Agenda de Eventos ")
    st.caption("Confira abaixo os horários já reservados ou edite suas próprias reservas ativas.")
    
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
        # "Todos (Incluindo Passados)" não aplica filtro adicional de data aqui
            
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
                card_style = "📆 **[Minha Reserva]** " if is_meu_evento else "📌 "
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    
                    with c1:
                        st.markdown(f"{card_style}**{ev['titulo']}**")
                    with c2:
                        st.markdown(f"🕒 `{data_str}` | **{hora_ini_str} às {hora_fim_str}**")
                    with c3:
                        if is_meu_evento:
                            b_edit, b_del = st.columns(2)
                            
                            with b_edit:
                                is_editing_this = st.session_state["editando_reserva_id"] == ev["id"]
                                txt_edit_btn = "✖️ Fechar" if is_editing_this else "✏️ Editar"
                                st.button(
                                    txt_edit_btn, 
                                    key=f"btn_edit_trigger_{ev['id']}", 
                                    use_container_width=True, 
                                    on_click=alternar_edicao_callback, 
                                    args=(ev["id"],)
                                )
                                
                            with b_del:
                                with st.popover("❌ Cancelar", use_container_width=True):
                                    st.markdown("⚠️ **Confirmar exclusão?**")
                                    st.caption("Essa ação não poderá ser desfeita.")
                                    
                                    pc1, pc2 = st.columns(2)
                                    with pc1:
                                        if st.button("Sim, Excluir", key=f"conf_del_{ev['id']}", type="primary", use_container_width=True):
                                            supabase.table("agendamentos").delete().eq("id", ev["id"]).execute()
                                            st.rerun()
                                    with pc2:
                                        if st.button("Voltar", key=f"canc_del_{ev['id']}", use_container_width=True):
                                            st.rerun()
                    
                    if is_meu_evento and st.session_state["editando_reserva_id"] == ev["id"]:
                        with st.container(border=True):
                            st.markdown("#### ✏️ Alterar dados da minha reserva")
                            with st.form(key=f"edit_form_{ev['id']}"):
                                new_title = st.text_input("Título", value=ev["titulo"])
                                new_date = st.date_input("Data", value=dt_ini_obj.date(), min_value=hoje)
                                
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    new_start = st.time_input("Início", value=dt_ini_obj.time())
                                with ec2:
                                    new_end = st.time_input("Término", value=dt_fim_obj.time())
                                
                                fc_1, fc_2 = st.columns([1, 4])
                                with fc_1:
                                    submit_edit = st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                                
                                if submit_edit:
                                    agora = agora_local()
                                    
                                    if not new_title.strip():
                                        st.warning("O título não pode ficar em branco.")
                                    elif new_start >= new_end:
                                        st.error("O término deve ser posterior ao início.")
                                    elif new_date == hoje and new_start <= agora.time():
                                        st.error("⚠️ Você não pode alterar para um horário que já passou hoje.")
                                    else:
                                        new_dt_ini = datetime.combine(new_date, new_start).isoformat()
                                        new_dt_fim = datetime.combine(new_date, new_end).isoformat()
                                        
                                        conflitos = verificar_conflito(new_dt_ini, new_dt_fim, ignore_id=ev["id"])
                                        if conflitos:
                                            st.error(f"⚠️ Conflito com: **{conflitos[0]['titulo']}**.")
                                        else:
                                            try:
                                                supabase.table("agendamentos").update({
                                                    "titulo": new_title.strip(),
                                                    "data_inicio": new_dt_ini,
                                                    "data_fim": new_dt_fim
                                                }).eq("id", ev["id"]).execute()
                                                st.session_state["editando_reserva_id"] = None
                                                st.success("Atualizado!")
                                                st.rerun()
                                            except Exception as e:
                                                if "evita_sobreposicao_horario" in str(e):
                                                    st.error("⚠️ Outro agendamento foi feito para este mesmo horário milissegundos antes da sua alteração! Por favor, escolha outro período.")
                                                else:
                                                    st.error(f"Erro ao salvar: {e}")
