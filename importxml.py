import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from utils import extrair_dados_xml, calcular_defasagem_meses

def exportar_excel(df, nome_arquivo="relatorio.xlsx"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
    output.seek(0)
    return output

st.set_page_config(layout="wide")
st.title("📊 Projetor Fiscal & Financeiro via SPED")

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

        # 🔹 Se for coluna explicitamente monetária
        if col in colunas_monetarias:
            format_dict[col] = "R$ {:,.2f}"

        # 🔹 Se for coluna percentual
        elif "Participação" in col_str or "Margem" in col_str:
            format_dict[col] = "{:,.2f}%"

        # 🔹 Se for coluna mensal numérica (pivot)
        elif isinstance(col, pd.Period):
            format_dict[col] = "R$ {:,.2f}"

    return df.style.format(format_dict)

def formatar_apuracao(df):

    colunas_moeda = ["Crédito", "Débito", "Resultado (Débito - Crédito)"]

    format_dict = {}

    for col in df.columns:
        if col in colunas_moeda:
            format_dict[col] = "R$ {:,.2f}"

    return df.style.format(format_dict)

# =====================================================
# 🔒 CONTROLE DE SESSÃO
# =====================================================

if "df_base" not in st.session_state:
    st.session_state.df_base = pd.DataFrame()
    st.session_state.chaves = set()

# =====================================================
# 📥 IMPORTAÇÃO XML + CLASSIFICAÇÃO MANUAL
# =====================================================

st.subheader("Classificação da Operação dos XML")

tipo_manual = st.radio(
    "Os XML importados serão considerados como:",
    ["Automático (usar CFOP do XML)", "Entrada"],
    horizontal=True
)

uploaded_files = st.file_uploader(
    "Importar XML modelo 55",
    type=["xml"],
    accept_multiple_files=True
)

def converter_cfop(cfop_original, tipo_desejado):
    """
    Converte CFOP de saída (5,6,7) para entrada (1,2,3)
    apenas trocando o primeiro dígito.
    """
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

    for file in uploaded_files:
        resultado = extrair_dados_xml(file)

        if resultado and resultado["chave"] not in st.session_state.chaves:

            st.session_state.chaves.add(resultado["chave"])

            for venc in resultado["vencimentos"]:

                defasagem = calcular_defasagem_meses(
                    resultado["emissao"],
                    venc
                )

                cfop_original = str(resultado["cfop"]).strip()

                # Aplicar conversão conforme seleção do usuário
                if tipo_manual == "Entrada":
                    cfop_final = converter_cfop(cfop_original, "Entrada")
                else:
                    # Automático → mantém CFOP original
                    cfop_final = cfop_original

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
                    if cfop_original.startswith(("1", "2", "3")):
                        tipo_operacao = "Entrada"
                    else:
                        tipo_operacao = "Saída"

                    cfop_final = cfop_original

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

# ➤ Listas CFOP de venda
cfop_devolucao_venda = [
    "1201","1202","1203","1204","1205","1206","1207","1208","1209",
    "1410","1411",
    "1503","1504","1505","1506",
    "2201","2202","2203","2204","2205","2206","2207","2208","2209",
    "2410","2411",
    "2503","2504","2505","2506","2556"
]

cfop_outros = [
    # Bonificação / Doação / Brindes
    "5910","6910",
    "5911","6911",
    "5912","6912",

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

    # Transferências
    "5152","6152",
    "5153","6153",

    # Outras saídas sem receita
    "5949","6949"
]

# =====================================================
# 🔹 CLASSIFICAÇÃO
# =====================================================

# Vendas normais (Saída que NÃO é devolução)
df_vendas_normais = df[
    (df["tipo_operacao"] == "Saída") &
    (~df["cfop"].isin(cfop_devolucao_venda)) &
    (~df["cfop"].isin(cfop_devolucao_compra)) &
    (~df["cfop"].isin(cfop_outros))
]

# Compras normais (Entrada que NÃO é devolução)
df_compras_normais = df[
    (df["tipo_operacao"] == "Entrada") &
    (~df["cfop"].isin(cfop_devolucao_venda)) &
    (~df["cfop"].isin(cfop_devolucao_compra)) &
    (~df["cfop"].isin(cfop_outros))
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
frete_cif = df_vendas_normais["frete"].sum()

# =====================================================
# 🔹 EXIBIÇÃO
# =====================================================

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

col1.metric("Total Vendas (Bruto)", f"R$ {total_vendas:,.2f}")
col2.metric("Total Compras (Bruto)", f"R$ {total_compras:,.2f}")
col3.metric("Devoluções Venda", f"R$ {total_dev_venda:,.2f}")
col4.metric("Devoluções Compra", f"R$ {total_dev_compra:,.2f}")
col5.metric("Frete CIF (Saídas)", f"R$ {frete_cif:,.2f}")
col6.metric("Frete FOB (Entradas)", f"R$ {frete_fob:,.2f}")
col7.metric("Resultado Líquido", f"R$ {resultado_liquido:,.2f}")

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

    st.dataframe(formatar_moeda(resumo), use_container_width=True)

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

    impostos_lista = ["ICMS","ST","IPI","PIS","COFINS"]

    # =====================================================
    # 📌 SEPARAÇÃO CRÉDITO (Entrada) E DÉBITO (Saída)
    # =====================================================

    df_credito = df[df["tipo_operacao"]=="Entrada"]
    df_debito = df[df["tipo_operacao"]=="Saída"]

    credito = df_credito[impostos_lista].sum().to_frame(name="Crédito")
    debito = df_debito[impostos_lista].sum().to_frame(name="Débito")

    apuracao = pd.concat([credito, debito], axis=1).fillna(0)

    # =====================================================
    # 📌 RESULTADO (Exceto ST)
    # =====================================================

    apuracao["Resultado (Débito - Crédito)"] = (
        apuracao["Débito"] - apuracao["Crédito"]
    )

    # ST não entra no resultado
    if "ST" in apuracao.index:
        apuracao.loc["ST", "Resultado (Débito - Crédito)"] = None

    apuracao_exibicao = (
        apuracao
        .reset_index()
        .rename(columns={"index": "Imposto"})
    )

    st.dataframe(
        formatar_apuracao(apuracao_exibicao),
        use_container_width=True
    )

    # =====================================================
    # 📊 VISUAL GRÁFICO DÉBITO x CRÉDITO
    # =====================================================

    st.divider()
    st.subheader("Comparativo Débito x Crédito")

    grafico_df = apuracao.reset_index().rename(columns={"index":"Imposto"})

    fig_apuracao = px.bar(
        grafico_df,
        x="Imposto",
        y=["Débito","Crédito"],
        barmode="group"
    )

    st.plotly_chart(fig_apuracao, use_container_width=True)


# =====================================================
# 📅 FINANCEIRO + SIMULADOR
# =====================================================

with aba3:

    # =====================================================
    # 📅 MATRIZ DETALHADA DO FLUXO REAL
    # =====================================================

    df["mes_venc"] = df["vencimento"].dt.to_period("M")

    # cálculo de dias entre emissão e vencimento
    df["dias_emissao_venc"] = (
        df["vencimento"] - df["emissao"]
    ).dt.days

    # formatação padrão dd/mm/aaaa
    df["emissao_formatada"] = df["emissao"].dt.strftime("%d/%m/%Y")
    df["vencimento_formatado"] = df["vencimento"].dt.strftime("%d/%m/%Y")

    fluxo_real = df[[
        "emissao_formatada",
        "vencimento_formatado",
        "dias_emissao_venc",
        "mes_venc",
        "tipo_operacao",
        "valor"
    ]].copy()

    fluxo_real["mes_venc"] = fluxo_real["mes_venc"].astype(str)

    st.subheader("Fluxo Real Detalhado")
    st.dataframe(formatar_moeda(fluxo_real), use_container_width=True)

    # =====================================================
    # 📊 GRÁFICO MENSAL (mantém visão resumida)
    # =====================================================

    financeiro = (
        df.groupby(["mes_venc","tipo_operacao"])["valor"]
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

    df_pagamentos = df[df["tipo_operacao"]=="Entrada"]

    dist_pag = (
    df_pagamentos.groupby("defasagem")["valor"]
    .sum()
    .reset_index()
    )

    total_pag = dist_pag["valor"].sum()

    if total_pag > 0:

        dist_pag["percentual"] = dist_pag["valor"] / total_pag

        valor_pagar = st.number_input(
        "Valor de Compras para Projetar",
        value=0.0,
        step=10000.0
    )

    # usa o MESMO mes_base do simulador de receita
    # pois já foi definido acima
    if valor_pagar > 0:

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
    "2503","2504","2505","2506"
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

    # ==========================================
    # 🔹 CLASSIFICAÇÃO (igual ao Dashboard Executivo)
    # ==========================================

    # CFOP que não representam venda real
    cfop_outros = [
        "5910","6910","5911","6911","5912","6912",
        "5901","6901","5902","6902","5903","6903","5904","6904",
        "5905","6905","5906","6906","5907","6907","5908","6908","5909","6909",
        "5152","6152","5153","6153",
        "5949","6949"
    ]

    # Vendas normais (Saída que NÃO é devolução e NÃO é CFOP “sujeira”)
    df_vendas_normais = df[
        (df["tipo_operacao"] == "Saída") &
        (~df["cfop"].isin(cfop_devolucao_venda)) &
        (~df["cfop"].isin(cfop_devolucao_compra)) &
        (~df["cfop"].isin(cfop_outros))
    ]

    # Compras normais (Entrada que NÃO é devolução e NÃO é CFOP “sujeira”)
    df_compras_normais = df[
        (df["tipo_operacao"] == "Entrada") &
        (~df["cfop"].isin(cfop_devolucao_venda)) &
        (~df["cfop"].isin(cfop_devolucao_compra)) &
        (~df["cfop"].isin(cfop_outros))
    ]

    # Devolução de venda (Entrada)
    df_dev_venda = df[
        (df["tipo_operacao"] == "Entrada") &
        (df["cfop"].isin(cfop_devolucao_venda)) &
        (~df["cfop"].isin(cfop_outros))
    ]

    # Devolução de compra (Saída)
    df_dev_compra = df[
        (df["tipo_operacao"] == "Saída") &
        (df["cfop"].isin(cfop_devolucao_compra)) &
        (~df["cfop"].isin(cfop_outros))
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

    for col in dre.columns:
        if col in colunas_moeda_dre:
            format_dict_dre[col] = "R$ {:,.2f}"
        elif "Margem" in col:
            format_dict_dre[col] = "{:,.2f}%"

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
