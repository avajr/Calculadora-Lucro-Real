import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from utils import extrair_dados_xml, calcular_defasagem_meses

# =====================================================
# 🔒 GARANTIAS
# =====================================================
def validar_resultado_xml(resultado):
    """
    Valida o dicionário retornado por extrair_dados_xml.
    Se faltar qualquer campo essencial, retorna False.
    """

    campos_obrigatorios = [
        "chave",
        "emissao",
        "vencimentos",
        "valor",
        "cfop",
        "cnpj",
        "razao_social",
        "cnpj_destinatario",
        "razao_destinatario",
        "impostos"
    ]

    # Se resultado for None ou vazio → inválido
    if not resultado or not isinstance(resultado, dict):
        return False

    # Verificar campos obrigatórios
    for campo in campos_obrigatorios:
        if campo not in resultado:
            return False
        if resultado[campo] in [None, "", [], {}]:
            return False

    # Valor precisa ser numérico e > 0
    try:
        if float(resultado["valor"]) <= 0:
            return False
    except:
        return False

    # Vencimentos precisa ser lista válida
    if not isinstance(resultado["vencimentos"], list):
        return False

    return True

def exportar_excel(df, nome_arquivo="relatorio.xlsx"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
    output.seek(0)
    return output

st.set_page_config(page_title="📊 Projetor Fiscal & Financeiro", layout="wide")
st.title("📊 Projetor Fiscal & Financeiro")

st.set_page_config(
    page_title="🏦 Projeção Fiscal & Financeiro",
    page_icon="🏛️",   # ícone
    layout="wide"
)


# =====================================================
# 🛠 FUNÇÃO GLOBAL DE FORMATAÇÃO MONETÁRIA
# =====================================================

def formatar_moeda(df):

    colunas_monetarias = {
        "valor","frete","ICMS","ST","IPI","PIS","COFINS",
        "Receita Bruta","Compras","Resultado Bruto"
    }

    format_dict = {}

    for col in df.columns:

        col_str = str(col)

        if col in colunas_monetarias:
            format_dict[col] = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        elif "Participação" in col_str or "Margem" in col_str:
            format_dict[col] = lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

        elif isinstance(col, pd.Period):
            format_dict[col] = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return df.style.format(format_dict)

def formatar_apuracao(df):

    colunas_moeda = ["Crédito", "Débito", "Resultado (Débito - Crédito)"]

    format_dict = {}

    for col in df.columns:
        if col in colunas_moeda:
            format_dict[col] = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return df.style.format(format_dict)

# =====================================================
# 🔒 CONTROLE DE SESSÃO
# =====================================================

if "df_base" not in st.session_state:
    st.session_state.df_base = pd.DataFrame()
    st.session_state.chaves = set()

# =====================================================
# 🔹 AJUSTE DE CFOP
# =====================================================

# ➤ Listas CFOP outros
cfop_outros = [
    # Bonificação / Doação / Brindes
    "5910","6910",
    "5911","6911",
    "5912","6912",
    "5913","6913",
    "5914","6914",

    # Remessas (não geram receita)
    "5901","6901",
    "5902","6902",
    "5903","6903",
    "5904","6904",
    "5905","6905",
    "5906","6906",
    "5907","6907",
    "5908","6908",
    "5909","6909",
    "5915","6915",
    "5916","6916",
    "5917","6917",
    "5918","6918",
    "5919","6919",
    "5920","6920",
    "5921","6921",
    "5922","6922",
    "5923","6923",
    "5924","6924",
    "5925","6925",
    "5926","6926",
    "5927","6927",
    "5928","6928",
    "5929","6929",
    "5930","6930",
    "5931","6931",
    "5932","6932",
    "5933","6933",

    # Transferências
    "5152","6152",
    "5153","6153",

    # Outras saídas sem receita
    "5949","6949"
]


# =====================================================
# 📥 IMPORTAÇÃO XML + CLASSIFICAÇÃO MANUAL
# =====================================================

st.subheader("Classificação da Operação dos XML")

tipo_manual = st.radio(
    "Os XML importados serão considerados como:",
    ["Automático (usar CFOP do XML)", "Entrada"],
    horizontal=True
)

st.markdown("### 📥 Importação de Arquivos")

st.info("""
Você pode importar:
- **XML individuais**
- **Vários XML de uma vez**
- **Arquivos ZIP contendo milhares de XML**
""")

uploaded_files = st.file_uploader(
    "Selecione XML ou ZIP",
    type=["xml", "zip"],
    accept_multiple_files=True
)

def converter_cfop(cfop_original, tipo_desejado):
    if not cfop_original:
        return cfop_original

    cfop_original = str(cfop_original).strip()
    mapa_entrada = {"5": "1", "6": "2", "7": "3"}

    primeiro = cfop_original[0]

    if tipo_desejado == "Entrada" and primeiro in mapa_entrada:
        return mapa_entrada[primeiro] + cfop_original[1:]

    return cfop_original


df = st.session_state.df_base

if uploaded_files:

    novos = []
    arquivos_xml = []

    # =====================================================
    # 📦 SUPORTE A ZIP — extrair XML de dentro do ZIP
    # =====================================================
    import zipfile

    for file in uploaded_files:
        if file.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(file) as z:
                    for nome in z.namelist():
                        if nome.lower().endswith(".xml"):
                            buffer = BytesIO(z.read(nome))
                            buffer.name = nome  # 🔥 CORREÇÃO AQUI
                            arquivos_xml.append(buffer)
            except:
                st.error(f"Erro ao ler ZIP: {file.name}")
        else:
            arquivos_xml.append(file)

    # Agora arquivos_xml contém:
    # ✔ XML enviados individualmente
    # ✔ XML extraídos de ZIP

    for file in arquivos_xml:
        resultado = extrair_dados_xml(file)

        # 🔒 VALIDAR XML ANTES DE QUALQUER PROCESSAMENTO
        if not validar_resultado_xml(resultado):
            st.warning(f"XML ignorado por estar incompleto ou inválido: {file.name}")
            continue

        # 🔒 Impedir duplicação
        if resultado["chave"] in st.session_state.chaves:
            continue

        st.session_state.chaves.add(resultado["chave"])

        # 🔄 PARA CADA VENCIMENTO
        for venc in resultado["vencimentos"]:

            defasagem = calcular_defasagem_meses(
                resultado["emissao"],
                venc
            )

            cfop_original = str(resultado["cfop"]).strip()

            # ================================
            # 🔄 DEFINIÇÃO DO TIPO OPERAÇÃO
            # ================================
            if tipo_manual == "Entrada":
                tipo_operacao = "Entrada"
                cfop_final = converter_cfop(cfop_original, "Entrada")

            elif tipo_manual == "Saída":
                tipo_operacao = "Saída"
                cfop_final = converter_cfop(cfop_original, "Saída")

            else:
                # modo automático pelo CFOP original
                if cfop_original in cfop_outros:
                    # CFOPs especiais → categoria "Outros"
                    tipo_operacao = "Outros"
                    cfop_final = cfop_original  # não converte

                elif cfop_original.startswith(("1", "2", "3")):
                    tipo_operacao = "Entrada"
                    cfop_final = converter_cfop(cfop_original, "Entrada")

                else:
                    tipo_operacao = "Saída"
                    cfop_final = converter_cfop(cfop_original, "Saída")

            # ================================
            # 🔎 CLASSIFICAÇÃO DA NATUREZA
            # ================================
            novos.append({
                "tipo_operacao": tipo_operacao,
                "chave": resultado["chave"],
                "emissao": resultado["emissao"],
                "vencimento": venc,
                "valor": resultado["valor"] / len(resultado["vencimentos"]),
                "frete": resultado.get("frete", 0.0) / len(resultado["vencimentos"]),
                "cfop": cfop_final,
                "cnpj": resultado["cnpj"],
                "razao_social": resultado["razao_social"],
                "cnpj_destinatario": resultado["cnpj_destinatario"],
                "razao_destinatario": resultado["razao_destinatario"],
                "defasagem": defasagem,
                **resultado["impostos"]
            })

    # 🔄 ADICIONAR AO DATAFRAME FINAL
    if novos:
        df_novo = pd.DataFrame(novos)
        st.session_state.df_base = pd.concat(
            [st.session_state.df_base, df_novo],
            ignore_index=True
        )


if df.empty:
    st.info("Importe XML para iniciar.")
    st.stop()


# =====================================================
# 🔐 GARANTIA DE TIPOS
# =====================================================

colunas_float = ["valor","frete","ICMS","ST","IPI","PIS","COFINS"]
for col in colunas_float:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

df["emissao"] = pd.to_datetime(df["emissao"], errors="coerce")
df["vencimento"] = pd.to_datetime(df["vencimento"], errors="coerce")
df["defasagem"] = pd.to_numeric(df["defasagem"], errors="coerce").fillna(0)

st.success(f"{df['chave'].nunique()} notas carregadas")

# =====================================================
# 📈 DASHBOARD EXECUTIVO
# =====================================================

st.divider()
st.subheader("📈 Dashboard Executivo")

# 🔧 Garantir CFOP como string
df["cfop"] = df["cfop"].astype(str).str.strip()

# ➤ Listas CFOP devolução compra
cfop_devolucao_compra = [
    "5201","5202","5203","5204","5205","5206","5207","5208","5209",
    "5410","5411",
    "5503","5504","5505","5506",
    "6201","6202","6203","6204","6205","6206","6207","6208","6209",
    "6410","6411","6413",
    "6503","6504","6505","6506",
    "6556"
]

# ➤ Listas CFOP devolução venda
cfop_devolucao_venda = [
    "1201","1202","1203","1204","1205","1206","1207","1208","1209",
    "1410","1411",
    "1503","1504","1505","1506",
    "2201","2202","2203","2204","2205","2206","2207","2208","2209",
    "2410","2411",
    "2503","2504","2505","2506","2556"
]


# =====================================================
# 🔹 CLASSIFICAÇÃO
# =====================================================

# Vendas normais (Saída que NÃO é devolução)
df_vendas_normais = df[
    (df["tipo_operacao"] == "Saída") &
    (~df["cfop"].isin(cfop_devolucao_venda)) &
    (~df["cfop"].isin(cfop_devolucao_compra))
]

# Compras normais (Entrada que NÃO é devolução)
df_compras_normais = df[
    (df["tipo_operacao"] == "Entrada") &
    (~df["cfop"].isin(cfop_devolucao_venda)) &
    (~df["cfop"].isin(cfop_devolucao_compra))
]

# Devolução de venda (Entrada)
df_dev_venda = df[
    (df["tipo_operacao"] == "Entrada") &
    (df["cfop"].isin(cfop_devolucao_venda))
]

# Devolução de compra (Saída)
df_dev_compra = df[
    (df["tipo_operacao"] == "Saída") &
    (df["cfop"].isin(cfop_devolucao_compra))
]

# =====================================================
# 🔹 CÁLCULOS COM AJUSTE NEGATIVO NO BRUTO
# =====================================================

# Vendas Brutas = Saídas normais - devolução de venda
total_vendas = df_vendas_normais["valor"].sum() - df_dev_venda["valor"].sum()

# Compras Brutas = Entradas normais - devolução de compra
total_compras = df_compras_normais["valor"].sum() - df_dev_compra["valor"].sum()

# Devoluções (sempre positivas)
total_dev_venda = df_dev_venda["valor"].sum()
total_dev_compra = df_dev_compra["valor"].sum()

# Resultado líquido simplificado
resultado_liquido = total_vendas - total_compras

# Fretes
frete_fob = df_compras_normais["frete"].sum()
frete_cif = df[df["tipo_operacao"].isin(["Saída","Outros"])]["frete"].sum()

# =====================================================
# 🔹 EXIBIÇÃO
# =====================================================

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

fmt = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

col1.metric("Total Vendas (Bruto)", fmt(total_vendas))
col2.metric("Total Compras (Bruto)", fmt(total_compras))
col3.metric("Devoluções Venda", fmt(total_dev_venda))
col4.metric("Devoluções Compra", fmt(total_dev_compra))
col5.metric("Frete CIF (Saídas)", fmt(frete_cif))
col6.metric("Frete FOB (Entradas)", fmt(frete_fob))
col7.metric("Resultado Líquido", fmt(resultado_liquido))

# =====================================================
# 🧠 ABAS
# =====================================================

aba1, aba2, aba3, aba4 = st.tabs(
    ["📘 Bloco C",
     "📊 Apuração",
     "📅 Financeiro",
     "📑 DRE & Margens"]
)

# =====================================================
# 📘 BLOCO C
# =====================================================

with aba1:

    resumo = (
        df.groupby(["chave","tipo_operacao","emissao","cfop","cnpj","razao_social"])
        .agg({
            "valor":"sum",
            "frete":"sum",
            "ICMS":"sum",
            "ST":"sum",
            "IPI":"sum",
            "PIS":"sum",
            "COFINS":"sum"
        })
        .reset_index()
    )

    # ================================
    # 📄 PAGINAÇÃO (200 por página)
    # ================================

    linhas_por_pagina = 200
    total_linhas = len(resumo)
    total_paginas = (total_linhas // linhas_por_pagina) + (1 if total_linhas % linhas_por_pagina else 0)

    # Criar estado da página
    if "pagina_bloco_c" not in st.session_state:
        st.session_state.pagina_bloco_c = 1

    # Botões de navegação
    col1, col2, col3, col4, col5 = st.columns([1,1,4,1,1])

    with col1:
        if st.button("⬅️ Anterior"):
            st.session_state.pagina_bloco_c -= 1

    with col5:
        if st.button("Próxima ➡️"):
            st.session_state.pagina_bloco_c += 1

    # 🔒 CLAMP — impede valores inválidos
    st.session_state.pagina_bloco_c = max(1, min(st.session_state.pagina_bloco_c, total_paginas))

    # Exibir números de página estilo Google
    with col3:
        st.write(
            " | ".join(
                [
                    f"**{i}**" if i == st.session_state.pagina_bloco_c else str(i)
                    for i in range(1, total_paginas + 1)
                ]
            )
        )

    pagina = st.session_state.pagina_bloco_c

    inicio = (pagina - 1) * linhas_por_pagina
    fim = inicio + linhas_por_pagina

    resumo_paginado = resumo.iloc[inicio:fim]

    st.subheader(f"Bloco C — Página {pagina} de {total_paginas}")
    st.dataframe(formatar_moeda(resumo_paginado), use_container_width=True)

    # 📥 Botão Exportar Excel - Bloco C
    excel_file = exportar_excel(resumo, "bloco_c.xlsx")

    st.download_button(
        label="📥 Baixar Bloco C em Excel",
        data=excel_file,
        file_name="bloco_c.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =====================================================
# 📊 APURAÇÃO (CRÉDITO x DÉBITO)
# =====================================================

with aba2:

    st.subheader("📊 Apuração Fiscal - Crédito x Débito")

    # ================================
    # 🔄 Seleção do Regime Tributário
    # ================================
    regime = st.radio(
        "Selecione o regime tributário",
        ["Lucro Presumido", "Lucro Real"],
        horizontal=True
    )

    # ================================
    # 📌 Separação Crédito e Débito (ICMS, ST, IPI)
    # ================================
    impostos_xml = ["ICMS", "ST", "IPI"]

    df_credito = df[df["tipo_operacao"].isin(["Entrada","Outros"])]
    df_debito = df[df["tipo_operacao"].isin(["Saída","Outros"])]
   
    if df_debito.empty:
        st.info("Nenhuma operação de SAÍDA encontrada. Exibindo apenas dados de ENTRADA.")

    credito_xml = df_credito[impostos_xml].sum().to_frame(name="Crédito")
    debito_xml = df_debito[impostos_xml].sum().to_frame(name="Débito")

    # ================================
    # 📌 Bases de cálculo
    # ================================
    total_vendas = df_debito["valor"].sum() if not df_debito.empty else 0
    total_compras = df_credito["valor"].sum()

    # ================================
    # 📌 Cálculo dos impostos calculados
    # ================================
    if regime == "Lucro Presumido":

        # Débito (vendas)
        pis_debito = total_vendas * 0.0065
        cofins_debito = total_vendas * 0.03
        csll_debito = total_vendas * 0.12 * 0.09

        base_irpj = total_vendas * 0.08
        irpj_debito = base_irpj * 0.15 + max(base_irpj - 20000, 0) * 0.10

        # Crédito (compras)
        pis_credito = total_compras * 0.0065
        cofins_credito = total_compras * 0.03

    else:  # Lucro Real

        # Crédito (compras)
        pis_credito = total_compras * 0.0165
        cofins_credito = total_compras * 0.076

        # Débito (vendas)
        pis_debito = total_vendas * 0.0165
        cofins_debito = total_vendas * 0.076

        # Base real para IRPJ e CSLL
        base_real = max(total_vendas - total_compras, 0)

        csll_debito = base_real * 0.09
        irpj_debito = base_real * 0.15 + max(base_real - 20000, 0) * 0.10

    # 🔒 GARANTIR QUE O SISTEMA FUNCIONE SEM SAÍDAS
    if total_vendas == 0:
        pis_debito = 0
        cofins_debito = 0
        csll_debito = 0
        irpj_debito = 0

    # ================================
    # 📌 Montar tabela dos impostos calculados
    # ================================
    calculados = pd.DataFrame({
        "Imposto": ["PIS", "COFINS", "CSLL", "IRPJ"],
        "Crédito": [pis_credito, cofins_credito, 0, 0],
        "Débito": [pis_debito, cofins_debito, csll_debito, irpj_debito]
    })

    # ================================
    # 📌 Montar tabela final (XML + calculados)
    # ================================
    apuracao_xml = credito_xml.join(debito_xml).reset_index().rename(columns={"index": "Imposto"})

    apuracao = pd.concat([apuracao_xml, calculados], ignore_index=True)

    # Resultado
    apuracao["Resultado (Débito - Crédito)"] = apuracao["Débito"] - apuracao["Crédito"]

    # ST não entra no resultado
    apuracao.loc[apuracao["Imposto"] == "ST", "Resultado (Débito - Crédito)"] = None

    st.dataframe(formatar_apuracao(apuracao), use_container_width=True)

    # ================================
    # 📊 Gráfico
    # ================================
    st.divider()
    st.subheader("Comparativo Débito x Crédito")

    fig_apuracao = px.bar(
        apuracao,
        x="Imposto",
        y=["Débito", "Crédito"],
        barmode="group"
    )

    st.plotly_chart(fig_apuracao, use_container_width=True)

# =====================================================
# 📅 FINANCEIRO + SIMULADOR
# =====================================================

with aba3:

    # =====================================================
    # 📅 MATRIZ DETALHADA DO FLUXO REAL (AGRUPADA POR MÊS)
    # =====================================================

    df["mes_emissao"] = df["emissao"].dt.to_period("M")
    df["mes_venc"] = df["vencimento"].dt.to_period("M")

    fluxo_real = (
        df.groupby(["mes_emissao", "mes_venc", "tipo_operacao"])["valor"]
        .sum()
        .reset_index()
    )

    fluxo_real["mes_emissao"] = fluxo_real["mes_emissao"].astype(str)
    fluxo_real["mes_venc"] = fluxo_real["mes_venc"].astype(str)

    st.subheader("Fluxo Real Detalhado (Agrupado por Mês)")
    st.dataframe(formatar_moeda(fluxo_real), use_container_width=True)

    # =====================================================
    # 📊 GRÁFICO MENSAL (mantém visão resumida)
    # =====================================================

    financeiro = (
        df.groupby(["mes_venc", "tipo_operacao"])["valor"]
        .sum()
        .reset_index()
    )

    financeiro["mes_venc"] = financeiro["mes_venc"].astype(str)

    fig_fluxo = px.bar(
        financeiro,
        x="mes_venc",
        y="valor",
        color="tipo_operacao",
        barmode="group"
    )

    st.plotly_chart(fig_fluxo, use_container_width=True)

    # =====================================================
    # 🔮 SIMULADOR DE RECEITA
    # =====================================================

    st.divider()
    st.subheader("📅 Configuração da Projeção")

    mes_base = st.date_input("Mês Base da Projeção")

    st.divider()
    st.subheader("🔮 Simulador de Receita Futura")

    df_receita = df[df["tipo_operacao"]=="Saída"]

    distribuicao = (
        df_receita.groupby("defasagem")["valor"]
        .sum()
        .reset_index()
    )

    total = distribuicao["valor"].sum()

    if total > 0:

        distribuicao["percentual"] = distribuicao["valor"] / total

        valor_projetar = st.number_input(
            "Valor de Receita para Projetar",
            value=0.0,
            step=10000.0
        )

        if valor_projetar > 0:

            proj = []

            for _, row in distribuicao.iterrows():

                nova_data = pd.to_datetime(mes_base) + pd.DateOffset(
                    months=int(row["defasagem"])
                )

                proj.append({
                    "mes": str(nova_data.to_period("M")),  # ✅ CORREÇÃO AQUI
                    "valor": valor_projetar * row["percentual"]
                })

            df_proj = pd.DataFrame(proj)
            df_proj = df_proj.groupby("mes")["valor"].sum().reset_index()

            st.dataframe(formatar_moeda(df_proj), use_container_width=True)

            fig_proj = px.bar(df_proj, x="mes", y="valor")
            st.plotly_chart(fig_proj, use_container_width=True)

    # =====================================================
    # 🔮 SIMULADOR DE PAGAMENTOS FUTUROS (FORNECEDORES)
    # =====================================================

    st.divider()
    st.subheader("🔮 Simulador de Pagamentos Futuros (Fornecedores)")

    df_pagamentos = df[df["tipo_operacao"] == "Entrada"]

    dist_pag = (
        df_pagamentos.groupby("defasagem")["valor"]
        .sum()
        .reset_index()
    )

    total_pag = dist_pag["valor"].sum()

    # Campo de valor SEMPRE aparece
    valor_pagar = st.number_input(
        "Valor de Compras para Projetar",
        value=0.0,
        step=10000.0
    )

    # Só roda a simulação se houver dados E valor > 0
    if total_pag > 0 and valor_pagar > 0:

        dist_pag["percentual"] = dist_pag["valor"] / total_pag

        proj_pag = []

        for _, row in dist_pag.iterrows():

            nova_data = pd.to_datetime(mes_base) + pd.DateOffset(
                months=int(row["defasagem"])
            )

            proj_pag.append({
                "mes": str(nova_data.to_period("M")),
                "valor": valor_pagar * row["percentual"]
            })

        df_proj_pag = pd.DataFrame(proj_pag)
        df_proj_pag = df_proj_pag.groupby("mes")["valor"].sum().reset_index()

        st.dataframe(formatar_moeda(df_proj_pag), use_container_width=True)

        fig_proj_pag = px.bar(df_proj_pag, x="mes", y="valor")
        st.plotly_chart(fig_proj_pag, use_container_width=True)

# =====================================================
# 📑 DRE & MARGENS
# =====================================================

with aba4:

    st.subheader("DRE Mensal Automática")

    df["mes"] = df["emissao"].dt.to_period("M")

    # ==========================================
    # 🔹 DEFINIÇÃO DE CFOP DE DEVOLUÇÃO
    # ==========================================

    # ➤ Listas CFOP de venda
    cfop_devolucao_venda = [
    "1201","1202","1203","1204","1205","1206","1207","1208","1209",
    "1410","1411",
    "1503","1504","1505","1506",
    "2201","2202","2203","2204","2205","2206","2207","2208","2209",
    "2410","2411",
    "2503","2504","2505","2506","2556"
    ]

    # ➤ Listas CFOP de compra
    cfop_devolucao_compra = [
    "5201","5202","5203","5204","5205","5206","5207","5208","5209",
    "5410","5411",
    "5503","5504","5505","5506",
    "6201","6202","6203","6204","6205","6206","6207","6208","6209",
    "6410","6411","6413",
    "6503","6504","6505","6506",
    "6556"
    ]

    # Vendas normais (Saída que NÃO é devolução)
    df_vendas_normais = df[
        (df["tipo_operacao"] == "Saída") &
        (~df["cfop"].isin(cfop_devolucao_venda)) &
        (~df["cfop"].isin(cfop_devolucao_compra))
    ]

    # Compras normais (Entrada que NÃO é devolução)
    df_compras_normais = df[
        (df["tipo_operacao"] == "Entrada") &
        (~df["cfop"].isin(cfop_devolucao_venda)) &
        (~df["cfop"].isin(cfop_devolucao_compra))
    ]

    # Devolução de venda (Entrada)
    df_dev_venda = df[
        (df["tipo_operacao"] == "Entrada") &
        (df["cfop"].isin(cfop_devolucao_venda))
    ]

    # Devolução de compra (Saída)
    df_dev_compra = df[
        (df["tipo_operacao"] == "Saída") &
        (df["cfop"].isin(cfop_devolucao_compra))
    ]

    # ==========================================
    # 🔹 CÁLCULOS MENSAIS (igual ao Dashboard)
    # ==========================================

    receita_bruta = df_vendas_normais.groupby("mes")["valor"].sum()
    compras_bruta = df_compras_normais.groupby("mes")["valor"].sum()

    devolucao_venda = df_dev_venda.groupby("mes")["valor"].sum()
    devolucao_compra = df_dev_compra.groupby("mes")["valor"].sum()

    # ==========================================
    # 🔹 MONTAGEM DA MATRIZ DRE
    # ==========================================

    dre = pd.DataFrame({
        "Receita Bruta": receita_bruta,
        "Devolução Venda": devolucao_venda,
        "Compras Bruta": compras_bruta,
        "Devolução Compra": devolucao_compra
    }).fillna(0)

    # ==========================================
    # 🔹 AJUSTES LÍQUIDOS (igual ao Dashboard)
    # ==========================================

    dre["Receita Líquida"] = (
        dre["Receita Bruta"] - dre["Devolução Venda"]
    )

    dre["Compras Líquida"] = (
        dre["Compras Bruta"] - dre["Devolução Compra"]
    )

    dre["Resultado Bruto"] = (
        dre["Receita Líquida"] - dre["Compras Líquida"]
    )

    dre["Margem %"] = (
        dre["Resultado Bruto"] /
        dre["Receita Líquida"].replace(0, 1)
    ) * 100

    dre = dre.reset_index()
    dre["mes"] = dre["mes"].astype(str)
    # ==========================================
    # 🔹 FORMATAÇÃO LOCAL DA DRE
    # ==========================================

    colunas_moeda_dre = [
        "Receita Bruta",
        "Devolução Venda",
        "Compras Bruta",
        "Devolução Compra",
        "Receita Líquida",
        "Compras Líquida",
        "Resultado Bruto"
    ]

    format_dict_dre = {}

    fmt_moeda = lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fmt_percent = lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")

    for col in dre.columns:
        if col in colunas_moeda_dre:
            format_dict_dre[col] = fmt_moeda
        elif "Margem" in col:
            format_dict_dre[col] = fmt_percent

    st.dataframe(
        dre.style.format(format_dict_dre),
        use_container_width=True
    )
    
    # =====================================================
    # 🏢 AGREGAÇÃO POR CLIENTE (XML SAÍDA)
    # =====================================================

    st.divider()
    st.subheader("🏢 Agregador por Cliente (Saídas XML)")

    receita_cliente = (
        df[df["tipo_operacao"] == "Saída"]
        .groupby("razao_destinatario")["valor"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    total_cliente = receita_cliente["valor"].sum()

    if total_cliente > 0:

        receita_cliente["% Participação"] = (
            receita_cliente["valor"] / total_cliente * 100
        )

        total_row = pd.DataFrame({
            "razao_destinatario": ["TOTAL"],
            "valor": [receita_cliente["valor"].sum()],
            "% Participação": [receita_cliente["% Participação"].sum()]
        })

        receita_cliente = pd.concat(
            [receita_cliente, total_row],
            ignore_index=True
        )

        format_dict_cliente = {
            "valor": "R$ {:,.2f}",
            "% Participação": "{:,.2f}%"
        }

        st.dataframe(
            receita_cliente.style.format(format_dict_cliente),
            use_container_width=True
        )

    # =====================================================
    # 🏭 AGREGAÇÃO POR FORNECEDOR (XML ENTRADA)
    # =====================================================

    st.divider()
    st.subheader("🏭 Agregador por Fornecedor (Entradas XML)")

    receita_fornecedor = (
        df[df["tipo_operacao"] == "Entrada"]
        .groupby("razao_social")["valor"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    total_fornecedor = receita_fornecedor["valor"].sum()

    if total_fornecedor > 0:

        receita_fornecedor["% Participação"] = (
            receita_fornecedor["valor"] / total_fornecedor * 100
        )

        total_row_f = pd.DataFrame({
            "razao_social": ["TOTAL"],
            "valor": [receita_fornecedor["valor"].sum()],
            "% Participação": [receita_fornecedor["% Participação"].sum()]
        })

        receita_fornecedor = pd.concat(
            [receita_fornecedor, total_row_f],
            ignore_index=True
        )

        format_dict_fornecedor = {
            "valor": "R$ {:,.2f}",
            "% Participação": "{:,.2f}%"
        }

        st.dataframe(
            receita_fornecedor.style.format(format_dict_fornecedor),
            use_container_width=True
        )


