import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

# ============================
# CONFIGURAÇÃO DA PÁGINA
# ============================

st.set_page_config(layout="wide")

# ============================
# Funções de formatação
# ============================

def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor):
    return f"{valor*100:,.3f}%".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_numero(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ============================
# TÍTULO
# ============================

st.title("📊 Simulador Estratégico - Lucro Real")

st.subheader("Entradas")

# ============================
# INPUTS EM COLUNAS
# ============================

col1, col2, col3 = st.columns(3)

with col1:
    cmv = st.number_input("CMV", value=0.0, step=1000.0)
    despesa_total = st.number_input("Despesa Total", value=0.0, step=1000.0)
    despesa_dedutivel = st.number_input("Despesa Dedutível IRPJ", value=0.0, step=1000.0)

with col2:
    aliq_icms_credito = st.number_input("Alíquota Crédito ICMS (%)", value=0.00000, step=0.00001, format="%.5f") / 100
    aliq_icms_debito = st.number_input("Alíquota Débito ICMS (%)", value=0.00000, step=0.00001, format="%.5f") / 100
    custo_variavel_perc = st.number_input("Custos Variáveis (%)", value=0.00000, step=0.00001, format="%.5f") / 100

with col3:
    lucro_target = st.number_input("Lucro Target (%)", value=7.0) / 100
    tempo = st.selectbox("Tempo", ["Mensal", "Anual"])
    periodo = st.number_input("Período", value=1, step=1)

# ============================
# CÁLCULO
# ============================

if st.button("Calcular"):

    fator = periodo * 12 if tempo == "Anual" else periodo

    cmv_total = cmv * fator
    despesa_total_total = despesa_total * fator
    despesa_dedutivel_total = despesa_dedutivel * fator
    adicional_irpj_base = 20000 * fator

    aliq_pis_credito = 0.0925 * (1 - aliq_icms_credito)
    aliq_pis_debito = 0.0925 * (1 - aliq_icms_debito)

    soma_aliq_receita = aliq_icms_debito + aliq_pis_debito + custo_variavel_perc
    a = (1 - soma_aliq_receita) * (1 - 0.34)
    coeficiente_final = a - lucro_target

    credito_icms = cmv_total * aliq_icms_credito
    credito_pis = cmv_total * aliq_pis_credito

    base_lucro = cmv_total + despesa_total_total - (credito_icms + credito_pis)

    redutor_irpj = (
        (cmv_total + despesa_dedutivel_total - (credito_icms + credito_pis)) * 0.34
        + adicional_irpj_base * 0.10
    )

    receita_necessaria = (base_lucro - redutor_irpj) / coeficiente_final

    icms_pagar = (receita_necessaria * aliq_icms_debito) - credito_icms
    pis_pagar = (receita_necessaria * aliq_pis_debito) - credito_pis
    custo_variavel = receita_necessaria * custo_variavel_perc

    base_irpj = (
        receita_necessaria
        - cmv_total
        - despesa_dedutivel_total
        - icms_pagar
        - pis_pagar
        - custo_variavel
    )

    adicional = max(base_irpj - adicional_irpj_base, 0) * 0.10
    irpj = base_irpj * 0.15 + adicional
    csll = base_irpj * 0.09

    lucro_final = (
        receita_necessaria
        - cmv_total
        - despesa_total_total
        - icms_pagar
        - pis_pagar
        - custo_variavel
        - irpj
        - csll
    )

    margem_final = lucro_final / receita_necessaria if receita_necessaria != 0 else 0
    markup = receita_necessaria / cmv_total if cmv_total != 0 else 0

    carga_efetiva = (icms_pagar + pis_pagar + irpj + csll) / receita_necessaria
    margem_contribuicao = (
        receita_necessaria - icms_pagar - pis_pagar - custo_variavel
    ) / receita_necessaria

    # ============================
    # RESUMO EXECUTIVO
    # ============================

    st.success(
        f"Receita necessária para atingir {formatar_percentual(lucro_target)}: "
        f"{formatar_moeda(receita_necessaria)}"
    )

    st.divider()
    st.header("📊 Indicadores Estratégicos")

    colA, colB, colC, colD = st.columns(4)

    colA.metric("Lucro Final", formatar_moeda(lucro_final))
    colB.metric("Margem Líquida", formatar_percentual(margem_final))
    colC.metric("📈 Markup", formatar_numero(markup))
    colD.metric("Carga Tributária Efetiva", formatar_percentual(carga_efetiva))

    st.metric("Margem de Contribuição", formatar_percentual(margem_contribuicao))

    # ============================
    # DETALHAMENTO EM CAIXAS
    # ============================

    with st.expander("📂 Detalhamento Completo"):
        st.write("CMV:", formatar_moeda(cmv_total))
        st.write("Despesa Total:", formatar_moeda(despesa_total_total))
        st.write("ICMS:", formatar_moeda(icms_pagar))
        st.write("PIS/COFINS:", formatar_moeda(pis_pagar))
        st.write("IRPJ:", formatar_moeda(irpj))
        st.write("CSLL:", formatar_moeda(csll))

    # ============================
    # GRÁFICO
    # ============================

    dados = pd.DataFrame({
        "Categoria": ["CMV", "Despesas", "Impostos", "Custo Variável", "Lucro"],
        "Valor": [
            cmv_total,
            despesa_total_total,
            icms_pagar + pis_pagar + irpj + csll,
            custo_variavel,
            lucro_final
        ]
    })

    st.bar_chart(dados.set_index("Categoria"))

    # ============================
    # EXPORTAR EXCEL
    # ============================

    excel_buffer = BytesIO()
    dados.to_excel(excel_buffer, index=False)
    st.download_button(
        label="📥 Exportar Excel",
        data=excel_buffer.getvalue(),
        file_name="simulacao_lucro_real.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ============================
    # EXPORTAR PDF
    # ============================

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Simulação - Lucro Real", styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Receita Necessária: {formatar_moeda(receita_necessaria)}", styles["Normal"]))
    elements.append(Paragraph(f"Lucro Final: {formatar_moeda(lucro_final)}", styles["Normal"]))
    elements.append(Paragraph(f"Margem Líquida: {formatar_percentual(margem_final)}", styles["Normal"]))

    doc.build(elements)

    st.download_button(
        label="📄 Exportar PDF",
        data=pdf_buffer.getvalue(),
        file_name="simulacao_lucro_real.pdf",
        mime="application/pdf"
    )
