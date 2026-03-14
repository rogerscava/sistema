import streamlit as st
import sqlite3
from datetime import datetime, date
import pandas as pd
from fpdf import FPDF
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CALFER - SISTEMA DE OP", layout="wide")

# Estilo para botões iguais, MAIÚSCULAS e cores
st.markdown("""
    <style>
    .main { background: linear-gradient(to bottom, #ADD8E6, #00008B); color: white; }
    [data-testid="stSidebar"] { background-color: #001f3f; }
    
    /* Botões da lateral com tamanho fixo e iguais */
    section[data-testid="stSidebar"] .stButton button {
        width: 100% !important;
        height: 55px !important;
        border-radius: 8px;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 5px;
        display: block;
    }
    
    input, label, div, span, button, select, .stSelectbox { text-transform: uppercase !important; }
    div[data-testid="stProgress"] > div > div > div > div { background-color: #32CD32 !important; }
    .perc-texto { font-weight: bold; color: #32CD32; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO AUXILIAR PARA DOWNLOAD AUTOMÁTICO ---
def disparar_download(dados_pdf, nome_arquivo):
    b64 = base64.b64encode(dados_pdf).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{nome_arquivo}" id="download_link"></a>'
    st.markdown(href, unsafe_allow_html=True)
    st.markdown("<script>document.getElementById('download_link').click();</script>", unsafe_allow_html=True)

# --- FUNÇÃO GERAR PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'CALFER - RELATORIO DE PRODUCAO', 0, 1, 'C')
        self.ln(5)

def gerar_pdf_corpo(lista_ops, conn):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    if len(lista_ops) == 1:
        op_cod = lista_ops[0]
        pdf.add_page()
        op = pd.read_sql_query("SELECT * FROM ordens_producao WHERE codigo_op=?", conn, params=(op_cod,)).iloc[0]
        h = pd.read_sql_query("SELECT setor, data_entrada FROM historico_setores WHERE codigo_op=?", conn, params=(op_cod,))
        
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, f"DETALHAMENTO OP: {op['codigo_op']}", 1, 1, 'C', fill=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, f"CLIENTE: {op['cliente']} | QTD: {op['quantidade']} | COORDENADOR: {op['coordenador']}", 0, 1)
        pdf.cell(0, 8, f"MAQUINA: {op['maquina']} (DES: {op['maq_desenho']})", 0, 1)
        pdf.cell(0, 8, f"CONJUNTO: {op['conjunto']} (DES: {op['conj_desenho']})", 0, 1)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(60, 10, 'SETOR', 1); pdf.cell(70, 10, 'ENTRADA', 1); pdf.cell(60, 10, 'PERMANENCIA', 1); pdf.ln()
        pdf.set_font("Arial", '', 10)
        
        for i in range(len(h)):
            entrada = pd.to_datetime(h.iloc[i]['data_entrada'])
            saida = pd.to_datetime(h.iloc[i+1]['data_entrada']) if i+1 < len(h) else pd.to_datetime(op['data_finalizacao'])
            diff = saida - entrada
            tempo = f"{int(diff.total_seconds()//3600)}H {int((diff.total_seconds()%3600)//60)}MIN"
            pdf.cell(60, 10, str(h.iloc[i]['setor']).upper(), 1)
            pdf.cell(70, 10, entrada.strftime('%d/%m/%Y %H:%M'), 1)
            pdf.cell(60, 10, tempo, 1); pdf.ln()
    else:
        pdf.add_page('L')
        pdf.set_font("Arial", 'B', 8)
        cols = [25, 40, 40, 40, 15, 35, 35, 35]
        headers = ['OP', 'CLIENTE', 'MAQUINA', 'CONJUNTO', 'QTD', 'COORD', 'INICIO', 'FINAL']
        for i, h_text in enumerate(headers): pdf.cell(cols[i], 10, h_text, 1)
        pdf.ln()
        pdf.set_font("Arial", '', 7)
        for op_cod in lista_ops:
            row = pd.read_sql_query("SELECT * FROM ordens_producao WHERE codigo_op=?", conn, params=(op_cod,)).iloc[0]
            pdf.cell(cols[0], 10, str(row['codigo_op']), 1)
            pdf.cell(cols[1], 10, str(row['cliente'])[:20], 1)
            pdf.cell(cols[2], 10, str(row['maquina'])[:20], 1)
            pdf.cell(cols[3], 10, str(row['conjunto'])[:20], 1)
            pdf.cell(cols[4], 10, str(row['quantidade']), 1)
            pdf.cell(cols[5], 10, str(row['coordenador'])[:15], 1)
            pdf.cell(cols[6], 10, str(row['data_criacao'])[2:16], 1)
            pdf.cell(cols[7], 10, str(row['data_finalizacao'])[2:16], 1); pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# --- BANCO DE DADOS ---
def init_db():
    with sqlite3.connect('calfer_sistema.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS maquinas (id INTEGER PRIMARY KEY, cliente_id INTEGER, nome TEXT, desenho TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS conjuntos (id INTEGER PRIMARY KEY, maquina_id INTEGER, nome TEXT, desenho TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS coordenadores (id INTEGER PRIMARY KEY, nome TEXT, funcao TEXT)')
        c.execute('''CREATE TABLE IF NOT EXISTS ordens_producao 
                     (id INTEGER PRIMARY KEY, codigo_op TEXT, cliente TEXT, maquina TEXT, maq_desenho TEXT, 
                      conjunto TEXT, conj_desenho TEXT, coordenador TEXT, quantidade INTEGER,
                      setor_atual TEXT, status TEXT, data_criacao TIMESTAMP, data_finalizacao TIMESTAMP,
                      roteiro TEXT)''')
        c.execute('CREATE TABLE IF NOT EXISTS historico_setores (codigo_op TEXT, setor TEXT, data_entrada TIMESTAMP)')
init_db()

def resetar_banco():
    with sqlite3.connect('calfer_sistema.db') as conn:
        for t in ["clientes", "maquinas", "conjuntos", "coordenadores", "ordens_producao", "historico_setores"]:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
    init_db()

# --- NAVEGAÇÃO ---
if 'menu' not in st.session_state: st.session_state.menu = "Painel"
if 'roteiro' not in st.session_state: st.session_state.roteiro = []

with st.sidebar:
    st.image("https://iili.io/qaP6hNf.png", width=150)
    st.title("SISTEMA CALFER")
    if st.button("📊 PAINEL DE STATUS"): st.session_state.menu = "Painel"
    if st.button("📝 CRIAR NOVA OP"): st.session_state.menu = "Criar"; st.session_state.roteiro = []
    if st.button("✅ OP CONCLUÍDAS"): st.session_state.menu = "Relatorio"
    if st.button("⚙️ CADASTROS / EDITAR"): st.session_state.menu = "Cadastros"
    
    st.markdown("---")
    with st.expander("🚨 ÁREA DO ADMINISTRADOR"):
        senha_adm = st.text_input("SENHA", type="password")
        if senha_adm == "Rncs@060188":
            st.subheader("EDIÇÃO MANUAL")
            with sqlite3.connect('calfer_sistema.db') as conn:
                ops_ativas = pd.read_sql_query("SELECT id, codigo_op, setor_atual, roteiro FROM ordens_producao WHERE status != 'FINALIZADO'", conn)
            
            if not ops_ativas.empty:
                op_sel_id = st.selectbox("OP PARA ALTERAR", ops_ativas['codigo_op'].tolist())
                dados_op = ops_ativas[ops_ativas['codigo_op'] == op_sel_id].iloc[0]
                novo_setor = st.selectbox("MOVER PARA SETOR", dados_op['roteiro'].split(","))
                
                if st.button("CONFIRMAR MUDANÇA"):
                    with sqlite3.connect('calfer_sistema.db') as conn:
                        conn.execute("UPDATE ordens_producao SET setor_atual=? WHERE codigo_op=?", (novo_setor, op_sel_id))
                        conn.execute("INSERT INTO historico_setores VALUES (?,?,?)", (op_sel_id, novo_setor, datetime.now()))
                    st.success(f"{op_sel_id} MOVIDA PARA {novo_setor}"); st.rerun()
            
            st.divider()
            if st.button("⚠️ APAGAR TODO O BD"):
                resetar_banco(); st.success("BANCO LIMPO!"); st.rerun()
        elif senha_adm != "":
            st.error("ACESSO NEGADO")

# --- ABA CADASTROS ---
if st.session_state.menu == "Cadastros":
    st.header("⚙️ GESTÃO DE CADASTROS")
    t1, t2 = st.tabs(["✨ NOVO REGISTRO", "✏️ EDITAR / APAGAR"])
    with t1:
        tipo = st.selectbox("TIPO", ["CLIENTE", "MÁQUINA", "CONJUNTO", "COORDENADOR"])
        with st.form("f_novo", clear_on_submit=True):
            if tipo == "CLIENTE":
                n = st.text_input("NOME DO CLIENTE")
                if st.form_submit_button("SALVAR"):
                    with sqlite3.connect('calfer_sistema.db') as conn: conn.execute("INSERT INTO clientes (nome) VALUES (?)", (n.upper(),))
                    st.success("SALVO!"); st.rerun()
            elif tipo == "MÁQUINA":
                with sqlite3.connect('calfer_sistema.db') as conn: clis = pd.read_sql_query("SELECT * FROM clientes", conn)
                c_sel = st.selectbox("CLIENTE", clis['nome'].tolist()) if not clis.empty else "NENHUM"
                n, d = st.text_input("NOME MÁQUINA"), st.text_input("Nº DESENHO")
                if st.form_submit_button("SALVAR"):
                    c_id = clis[clis['nome'] == c_sel]['id'].values[0]
                    with sqlite3.connect('calfer_sistema.db') as conn: conn.execute("INSERT INTO maquinas (cliente_id, nome, desenho) VALUES (?,?,?)", (int(c_id), n.upper(), d.upper()))
                    st.success("SALVO!"); st.rerun()
            elif tipo == "CONJUNTO":
                with sqlite3.connect('calfer_sistema.db') as conn: maqs = pd.read_sql_query("SELECT * FROM maquinas", conn)
                m_sel = st.selectbox("MÁQUINA", maqs['nome'].tolist()) if not maqs.empty else "NENHUMA"
                n, d = st.text_input("NOME CONJUNTO"), st.text_input("Nº DESENHO")
                if st.form_submit_button("SALVAR"):
                    m_id = maqs[maqs['nome'] == m_sel]['id'].values[0]
                    with sqlite3.connect('calfer_sistema.db') as conn: conn.execute("INSERT INTO conjuntos (maquina_id, nome, desenho) VALUES (?,?,?)", (int(m_id), n.upper(), d.upper()))
                    st.success("SALVO!"); st.rerun()
            elif tipo == "COORDENADOR":
                n, f = st.text_input("NOME"), st.text_input("FUNÇÃO")
                if st.form_submit_button("SALVAR"):
                    with sqlite3.connect('calfer_sistema.db') as conn: conn.execute("INSERT INTO coordenadores (nome, funcao) VALUES (?,?)", (n.upper(), f.upper()))
                    st.success("SALVO!"); st.rerun()
    with t2:
        cat = st.selectbox("EDITAR:", ["CLIENTE", "MÁQUINA", "CONJUNTO", "COORDENADOR"])
        with sqlite3.connect('calfer_sistema.db') as conn:
            if cat == "CLIENTE":
                df = pd.read_sql_query("SELECT * FROM clientes", conn)
                if not df.empty:
                    sel = st.selectbox("SELECIONE", df['nome'].tolist()); row = df[df.nome == sel].iloc[0]
                    with st.form("e_cli"):
                        v1 = st.text_input("NOME", row['nome'])
                        if st.form_submit_button("💾 ATUALIZAR"): conn.execute("UPDATE clientes SET nome=? WHERE id=?", (v1.upper(), int(row['id']))); st.rerun()
                        if st.form_submit_button("🗑️ APAGAR"): conn.execute("DELETE FROM clientes WHERE id=?", (int(row['id']),)); st.rerun()
            elif cat == "MÁQUINA":
                df = pd.read_sql_query("SELECT * FROM maquinas", conn)
                if not df.empty:
                    sel = st.selectbox("SELECIONE MÁQUINA", df['nome'].tolist()); row = df[df.nome == sel].iloc[0]
                    with st.form("e_maq"):
                        v1, v2 = st.text_input("NOME", row['nome']), st.text_input("DESENHO", row['desenho'])
                        if st.form_submit_button("💾 ATUALIZAR"): conn.execute("UPDATE maquinas SET nome=?, desenho=? WHERE id=?", (v1.upper(), v2.upper(), int(row['id']))); st.rerun()
                        if st.form_submit_button("🗑️ APAGAR"): conn.execute("DELETE FROM maquinas WHERE id=?", (int(row['id']),)); st.rerun()
            elif cat == "CONJUNTO":
                df = pd.read_sql_query("SELECT * FROM conjuntos", conn)
                if not df.empty:
                    sel = st.selectbox("SELECIONE CONJUNTO", df['nome'].tolist()); row = df[df.nome == sel].iloc[0]
                    with st.form("e_conj"):
                        v1, v2 = st.text_input("NOME", row['nome']), st.text_input("DESENHO", row['desenho'])
                        if st.form_submit_button("💾 ATUALIZAR"): conn.execute("UPDATE conjuntos SET nome=?, desenho=? WHERE id=?", (v1.upper(), v2.upper(), int(row['id']))); st.rerun()
                        if st.form_submit_button("🗑️ APAGAR"): conn.execute("DELETE FROM conjuntos WHERE id=?", (int(row['id']),)); st.rerun()

# --- ABA CRIAR OP ---
elif st.session_state.menu == "Criar":
    st.header("📝 NOVA ORDEM DE PRODUÇÃO")
    with sqlite3.connect('calfer_sistema.db') as conn:
        clis = pd.read_sql_query("SELECT * FROM clientes", conn)
        coords = pd.read_sql_query("SELECT * FROM coordenadores", conn)
    if not clis.empty:
        col1, col2 = st.columns(2)
        c_op = col1.selectbox("CLIENTE", clis['nome'].tolist())
        qtd_op = col2.number_input("QUANTIDADE", min_value=1, value=1, step=1)
        cli_id = clis[clis['nome'] == c_op]['id'].values[0]
        with sqlite3.connect('calfer_sistema.db') as conn: maqs = pd.read_sql_query(f"SELECT * FROM maquinas WHERE cliente_id={cli_id}", conn)
        m_op = st.selectbox("MÁQUINA", maqs['nome'].tolist()) if not maqs.empty else "NENHUMA"
        conj_op, m_des, c_des = "NENHUM", "", ""
        if not maqs.empty:
            m_id = maqs[maqs.nome == m_op]['id'].values[0]; m_des = maqs[maqs.nome == m_op]['desenho'].values[0]
            with sqlite3.connect('calfer_sistema.db') as conn: conjs = pd.read_sql_query(f"SELECT * FROM conjuntos WHERE maquina_id={m_id}", conn)
            conj_op = st.selectbox("CONJUNTO", conjs['nome'].tolist()) if not conjs.empty else "NENHUM"
            if not conjs.empty: c_des = conjs[conjs.nome == conj_op]['desenho'].values[0]
        coo_op = st.selectbox("COORDENADOR", coords['nome'].tolist()) if not coords.empty else "NENHUM"
        st.subheader("DEFINIR ROTEIRO (CLIQUE NA ORDEM)")
        cols = st.columns(6); sets = ["CORTE/DOBRA", "CALDEIRARIA", "SOLDA", "USINAGEM", "PINTURA", "EXPEDIÇÃO"]
        for i, s in enumerate(sets):
            label = f"{st.session_state.roteiro.index(s)+1}° - {s}" if s in st.session_state.roteiro else s
            if cols[i].button(label, key=f"btn_{s}"):
                if s not in st.session_state.roteiro: st.session_state.roteiro.append(s); st.rerun()
        if st.session_state.roteiro:
            st.info(f"CAMINHO: {' -> '.join([f'{i+1}° {s}' for i, s in enumerate(st.session_state.roteiro)])}")
            if st.button("🚀 GERAR ORDEM DE PRODUÇÃO"):
                with sqlite3.connect('calfer_sistema.db') as conn:
                    count = conn.execute("SELECT COUNT(*) FROM ordens_producao").fetchone()[0] + 1
                    cod = f"OP.{count:04d}/{datetime.now().strftime('%m-%y')}"
                    conn.execute("INSERT INTO ordens_producao (codigo_op, cliente, maquina, maq_desenho, conjunto, conj_desenho, coordenador, quantidade, setor_atual, status, data_criacao, roteiro) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (cod, c_op, m_op, m_des, conj_op, c_des, coo_op, qtd_op, st.session_state.roteiro[0], "PRODUÇÃO", datetime.now(), ",".join(st.session_state.roteiro)))
                    conn.execute("INSERT INTO historico_setores VALUES (?,?,?)", (cod, st.session_state.roteiro[0], datetime.now()))
                st.session_state.roteiro = []; st.success("GERADA!"); st.rerun()

# --- PAINEL DE STATUS ---
elif st.session_state.menu == "Painel":
    st.header("🏗️ PAINEL DE STATUS")
    with sqlite3.connect('calfer_sistema.db') as conn:
        ops = conn.execute("SELECT * FROM ordens_producao WHERE status != 'FINALIZADO'").fetchall()
    
    for op in ops:
        rot = op[13].split(","); pos = rot.index(op[9]) + 1
        prog_val = pos / len(rot)
        st.write(f"### {op[2]} | {op[3]} | QTD: {op[8]} (OP: {op[1]})")
        c_prog, c_perc = st.columns([9, 1])
        c_prog.progress(prog_val)
        c_perc.markdown(f"<p class='perc-texto'>{int(prog_val*100)}%</p>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([2, 2, 2, 4])
        prox = rot[pos] if pos < len(rot) else "FINALIZAR"
        if c1.button(f"🚀 {prox}", key=f"av_{op[0]}"):
            with sqlite3.connect('calfer_sistema.db') as conn:
                if pos < len(rot):
                    conn.execute("UPDATE ordens_producao SET setor_atual=? WHERE id=?", (prox, op[0]))
                    conn.execute("INSERT INTO historico_setores VALUES (?,?,?)", (op[1], prox, datetime.now()))
                else:
                    conn.execute("UPDATE ordens_producao SET status='FINALIZADO', data_finalizacao=? WHERE id=?", (datetime.now(), op[0]))
            st.rerun()
        if c2.button(f"📝 EDITAR", key=f"ed_{op[0]}"):
            st.session_state[f"edit_mode_{op[0]}"] = not st.session_state.get(f"edit_mode_{op[0]}", False)
        if c3.button(f"🗑️ EXCLUIR", key=f"del_{op[0]}"):
            with sqlite3.connect('calfer_sistema.db') as conn: conn.execute("DELETE FROM ordens_producao WHERE id=?", (op[0],))
            st.rerun()
        if st.session_state.get(f"edit_mode_{op[0]}", False):
            with st.form(f"form_ed_op_{op[0]}"):
                nova_maq = st.text_input("MAQUINA", op[3])
                novo_conj = st.text_input("CONJUNTO", op[5])
                nova_qtd = st.number_input("QUANTIDADE", value=op[8])
                if st.form_submit_button("💾 SALVAR"):
                    with sqlite3.connect('calfer_sistema.db') as conn:
                        conn.execute("UPDATE ordens_producao SET maquina=?, conjunto=?, quantidade=? WHERE id=?", (nova_maq.upper(), novo_conj.upper(), nova_qtd, op[0]))
                    st.session_state[f"edit_mode_{op[0]}"] = False; st.rerun()
        st.divider()

# --- ABA RELATÓRIO ---
elif st.session_state.menu == "Relatorio":
    st.header("✅ OP CONCLUÍDAS")
    d1, d2 = st.columns(2)
    ini, fim = d1.date_input("INÍCIO", date.today()), d2.date_input("FIM", date.today())
    
    with sqlite3.connect('calfer_sistema.db') as conn:
        df = pd.read_sql_query("SELECT * FROM ordens_producao WHERE status='FINALIZADO'", conn)
        
        if not df.empty:
            df['data_finalizacao'] = pd.to_datetime(df['data_finalizacao'])
            # Filtro por data
            df_f = df[(df['data_finalizacao'].dt.date >= ini) & (df['data_finalizacao'].dt.date <= fim)]
            
            if not df_f.empty:
                st.write("### SELECIONE AS OPs PARA O RELATÓRIO:")
                selecionadas = []
                
                # Criar uma lista de checkboxes para seleção
                for i, r in df_f.iterrows():
                    if st.checkbox(f"{r['codigo_op']} - {r['cliente']} | FINALIZADA EM: {r['data_finalizacao'].strftime('%d/%m/%Y')}", key=f"chk_{r['id']}"):
                        selecionadas.append(r['codigo_op'])
                
                if selecionadas:
                    # GERAR O PDF EM MEMÓRIA
                    pdf_bytes = gerar_pdf_corpo(selecionadas, conn)
                    
                    # BOTÃO DE DOWNLOAD NATIVO (Mais seguro e estável)
                    st.download_button(
                        label="📥 BAIXAR RELATÓRIO PDF",
                        data=pdf_bytes,
                        file_name=f"RELATORIO_CALFER_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                        mime="application/pdf"
                    )
                
                st.divider()
                st.subheader("LISTA GERAL NO PERÍODO")
                st.dataframe(df_f[["codigo_op", "cliente", "maquina", "quantidade", "coordenador", "data_criacao", "data_finalizacao"]], use_container_width=True)
            else:
                st.warning("NENHUMA OP FINALIZADA NESTE PERÍODO.")