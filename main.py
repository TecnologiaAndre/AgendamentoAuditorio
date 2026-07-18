import datetime
import os
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuração da Página
st.set_page_config(page_title="Painel do Auditório", layout="wide")

# ID da sua agenda principal compartilhada
ID_DA_AGENDA = 'tecnologia.andre@gertaxi.com.br'

SCOPES = ['https://www.googleapis.com/auth/calendar']
ARQUIVO_CHAVE = 'service_account.json'

# Dicionário simples para traduzir meses abreviados
MESES_PT = {
    "Jan": "JAN", "Feb": "FEV", "Mar": "MAR", "Apr": "ABR", 
    "May": "MAI", "Jun": "JUN", "Jul": "JUL", "Aug": "AGO", 
    "Sep": "SET", "Oct": "OUT", "Nov": "NOV", "Dec": "DEZ"
}

def conectar_com_robo():
    """Autentica na API do Google usando a Conta de Serviço (Robô)"""
    if not os.path.exists(ARQUIVO_CHAVE):
        st.error(f"Erro: O arquivo '{ARQUIVO_CHAVE}' não foi encontrado na pasta do projeto.")
        st.stop()
        
    credenciais = service_account.Credentials.from_service_account_file(
        ARQUIVO_CHAVE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credenciais)

def buscar_compromissos(service, max_resultados=50):
    """Busca os eventos agendados na agenda escolhida (incluindo o dia de hoje)"""
    hoje_inicio = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + '-03:00'
    
    events_result = service.events().list(
        calendarId=ID_DA_AGENDA, 
        timeMin=hoje_inicio,
        maxResults=max_resultados, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def criar_evento(service, resumo, email, nome, motivo, data, hora_inicio, hora_fim):
    """Cria um novo agendamento na agenda guardando metadados na descrição"""
    inicio_iso = f"{data}T{hora_inicio}:00"
    fim_iso = f"{data}T{hora_fim}:00"
    
    # Guardamos uma tag estruturada [EMAIL: xxx] na descrição para ler depois
    descricao_final = (
        f"Responsável: {nome}\n"
        f"Motivo: {motivo}\n"
        f"[EMAIL:{email.strip().lower()}]\n"
        f"Agendado via Painel Streamlit."
    )
    
    detalhes_evento = {
        'summary': resumo,
        'description': descricao_final,
        'start': {'dateTime': inicio_iso, 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': fim_iso, 'timeZone': 'America/Sao_Paulo'},
    }
    
    evento_criado = service.events().insert(calendarId=ID_DA_AGENDA, body=detalhes_evento).execute()
    return evento_criado

def deletar_evento(service, event_id):
    """Remove um evento da agenda usando o ID único"""
    service.events().delete(calendarId=ID_DA_AGENDA, eventId=event_id).execute()

# --- Inicialização da API ---
try:
    service_google = conectar_com_robo()
except Exception as e:
    st.error(f"Erro crítico de autenticação com o robô: {e}")
    st.stop()

# Busca os eventos uma única vez no início
try:
    eventos = buscar_compromissos(service_google, max_resultados=50)
except Exception as e:
    st.error(f"Erro ao ler os dados da agenda: {e}")
    eventos = []

# --- Interface Visual do Painel Público ---
st.title("🏢 Painel de Disponibilidade do Auditório")
st.markdown("Consulte os horários ocupados e gerencie seus agendamentos abaixo de forma simplificada.")
st.markdown("---")

col_visualizacao, col_formulario = st.columns([5, 4], gap="large")

with col_visualizacao:
    st.subheader("🗓️ Próximos Horários Reservados")
    
    if not eventos:
        st.info("O auditório está totalmente livre para os próximos dias!")
    else:
        # Define a quantidade de blocos quadrados por linha (3 se encaixa muito bem)
        cards_por_linha = 3
        
        # Cria as linhas de cards
        for i in range(0, len(eventos), cards_por_linha):
            colunas_da_linha = st.columns(cards_por_linha)
            
            for j in range(cards_por_linha):
                indice_evento = i + j
                if indice_evento < len(eventos):
                    item = eventos[indice_evento]
                    
                    inicio = item['start'].get('dateTime', item['start'].get('date'))
                    fim = item['end'].get('dateTime', item['end'].get('date'))
                    if 'T' in inicio:
                        dt_i = datetime.datetime.fromisoformat(inicio)
                        dt_f = datetime.datetime.fromisoformat(fim)
                        horario_f = f"{dt_i.strftime('%H:%M')} às {dt_f.strftime('%H:%M')}"
                    else:
                        dt_i = datetime.datetime.fromisoformat(inicio)
                        horario_f = "Dia Inteiro"
                    
                    dia = dt_i.strftime('%d')
                    mes = MESES_PT.get(dt_i.strftime('%b'), dt_i.strftime('%b')).upper()
                    ano = dt_i.strftime('%Y')
                    titulo = item.get('summary', 'Reservado 🔒')
                    
                    # Estrutura HTML em formato quadrado empilhado verticalmente
                    html_quadrado = f"""
                    <div style="
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: space-between;
                        background-color: #1e222b;
                        border-radius: 12px;
                        padding: 12px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
                        border-top: 4px solid #ff4b4b;
                        height: 140px;
                        box-sizing: border-box;
                        text-align: center;
                    ">
                        <!-- Bloco do Calendário (Topo) -->
                        <div style="
                            width: 55px;
                            background-color: #11141a;
                            border-radius: 6px;
                            overflow: hidden;
                            border: 1px solid #31363f;
                            margin-bottom: 6px;
                        ">
                            <div style="background-color: #ff4b4b; color: white; font-size: 10px; font-weight: bold; padding: 2px 0;">{mes}</div>
                            <div style="font-size: 18px; font-weight: bold; color: #ffffff; padding: 1px 0; line-height: 1.1;">{dia}</div>
                            <div style="font-size: 8px; color: #888888; padding-bottom: 2px;">{ano}</div>
                        </div>
                        
                        <!-- Detalhes do Evento (Texto e Horário) -->
                        <div style="width: 100%; flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                            <div style="
                                font-size: 12px; 
                                font-weight: bold; 
                                color: #f0f2f6; 
                                margin-bottom: 4px;
                                display: -webkit-box;
                                -webkit-line-clamp: 2;
                                -webkit-box-orient: vertical;
                                overflow: hidden;
                                text-overflow: ellipsis;
                                line-height: 1.2;
                            ">
                                {titulo}
                            </div>
                            <div style="font-size: 11px; color: #00ddff; font-weight: 500; margin-top: auto;">
                                🕒 {horario_f}
                            </div>
                        </div>
                    </div>
                    """
                    
                    with colunas_da_linha[j]:
                        components.html(html_quadrado, height=155)

with col_formulario:
    aba_reservar, aba_cancelar = st.tabs(["➕ Solicitar Reserva", "❌ Cancelar Agendamento"])
    
    # --- ABA 1: SOLICITAR RESERVA ---
    with aba_reservar:
        with st.form("form_reserva", clear_on_submit=True):
            nome_solicitante = st.text_input("Seu Nome / Setor responsável *", placeholder="Ex: João Silva (Financeiro)")
            email_solicitante = st.text_input("Seu E-mail Corporativo *", placeholder="Ex: joao.silva@gertaxi.com.br")
            motivo_reserva = st.text_input("Motivo da Reunião / Evento *", placeholder="Ex: Alinhamento de Metas")
            
            data_reserva = st.date_input("Data pretendida", min_value=datetime.date.today())
            
            col_h1, col_h2 = st.columns(2)
            hora_i = col_h1.time_input("Horário de Início", datetime.time(9, 0))
            hora_f = col_h2.time_input("Horário de Término", datetime.time(10, 0))
            
            botao_enviar = st.form_submit_button("Confirmar Agendamento", type="primary")
            
            if botao_enviar:
                if not nome_solicitante or not motivo_reserva or not email_solicitante:
                    st.warning("Por favor, preencha todos os campos obrigatórios (*).")
                elif "@" not in email_solicitante or "." not in email_solicitante:
                    st.error("Por favor, insira um endereço de e-mail válido.")
                elif hora_i >= hora_f:
                    st.error("O horário de término precisa ser maior que o horário de início.")
                else:
                    with st.spinner("Registrando sua reserva no Google Agenda..."):
                        try:
                            resumo_final = f"{motivo_reserva} ({nome_solicitante})"
                            
                            criar_evento(
                                service=service_google,
                                resumo=resumo_final,
                                email=email_solicitante,
                                nome=nome_solicitante,
                                motivo=motivo_reserva,
                                data=data_reserva.isoformat(),
                                hora_inicio=hora_i.strftime('%H:%M'),
                                hora_fim=hora_f.strftime('%H:%M')
                            )
                            st.success("🎉 Reserva realizada com sucesso!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"Não foi possível salvar o agendamento: {err}")

    # --- ABA 2: CANCELAR RESERVA ---
    with aba_cancelar:
        st.markdown("Selecione o agendamento e confirme seu e-mail para removê-lo.")
        
        if not eventos:
            st.info("Não há nenhum agendamento registrado para ser cancelado.")
        else:
            opcoes_cancelamento = []
            mapeamento_ids = {}
            mapeamento_emails = {}
            
            for item in eventos:
                ev_id = item['id']
                ev_titulo = item.get('summary', 'Sem título')
                ev_desc = item.get('description', '')
                inicio_raw = item['start'].get('dateTime', item['start'].get('date'))
                
                if 'T' in inicio_raw:
                    dt_formatada = datetime.datetime.fromisoformat(inicio_raw).strftime('%d/%m/%Y às %H:%M')
                else:
                    dt_formatada = datetime.datetime.fromisoformat(inicio_raw).strftime('%d/%m/%Y (Dia Todo)')
                
                texto_exibicao = f"{dt_formatada} - {ev_titulo}"
                opcoes_cancelamento.append(texto_exibicao)
                mapeamento_ids[texto_exibicao] = ev_id
                
                email_vinculado = ""
                if "[EMAIL:" in ev_desc and "]" in ev_desc:
                    try:
                        email_vinculado = ev_desc.split("[EMAIL:")[1].split("]")[0].strip().lower()
                    except IndexError:
                        email_vinculado = ""
                
                mapeamento_emails[texto_exibicao] = email_vinculado
            
            with st.form("form_cancelamento", clear_on_submit=True):
                evento_selecionado = st.selectbox("Escolha o agendamento *", options=opcoes_cancelamento)
                validacao_email = st.text_input("Digite o E-mail do responsável *", placeholder="Ex: seu.email@gertaxi.com.br")
                
                botao_deletar = st.form_submit_button("Excluir Agendamento Permanentemente", type="secondary")
                
                if botao_deletar:
                    if not validacao_email:
                        st.warning("Por favor, informe o e-mail para validar a exclusão.")
                    else:
                        id_para_deletar = mapeamento_ids[evento_selecionado]
                        email_esperado = mapeamento_emails[evento_selecionado]
                        email_digitado = validacao_email.strip().lower()
                        
                        if not email_esperado:
                            st.error("Este agendamento foi criado no modelo antigo sem e-mail ou diretamente pelo Google Agenda. Exclusão permitida apenas pelo administrador.")
                        elif email_digitado == email_esperado:
                            with st.spinner("Removendo agendamento do Google Agenda..."):
                                try:
                                    deletar_evento(service_google, id_para_deletar)
                                    st.success("❌ Agendamento cancelado com sucesso!")
                                    st.rerun()
                                except Exception as err:
                                    st.error(f"Erro ao tentar remover o evento: {err}")
                        else:
                            st.error("Validação recusada! O e-mail digitado não coincide com o responsável por este agendamento.")

# --- NOTA DE RODAPÉ (FOOTER) ---
st.markdown("---")
html_rodape = """
<div style="
    text-align: center; 
    padding: 10px 0; 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
    color: #888888; 
    font-size: 12px;
    letter-spacing: 0.5px;
">
    © 2026 GERTAXI. All Rights Reserved. | Desenvolvido por <strong style="color: #ff4b4b;">ANDRÉ GUIMARÃES</strong>
</div>
"""
st.markdown(html_rodape, unsafe_allow_html=True)
