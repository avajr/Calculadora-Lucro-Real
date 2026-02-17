import streamlit as st

st.title("Calculadora de Lucro Real")

# =============================
# Funções de formatação
# =============================

def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor):
    return f"{valor*100:,.3f}%".replace(",", "X").replace(".", ",").replace("X", ".")

# =============================
# Entradas do Usuário
# =============================

receita = st.number_input("Receita Bruta", value=0.0, step=1000.0)
cmv = st.number_input("CMV", value=0.0, step=1000.0)

icms_credito_perc = st.number_input("Crédito ICMS (%)", value=0.0) / 100
icms_debito_perc = st.number_input("Débito ICMS (%)", value=0.0) / 100

despesas_dedutiveis = st.number_input("Despesas Dedutíveis IRPJ", value=0.0, step=1000.0)
despesas_gerais = st.number_input("Despesas Gerais", value=0.0, step=1000.0)

custos_variaveis_perc = st.number_input("Custos Variáveis (%)", value=0.0) / 100

# =============================
# Botão de cálculo
# =============================

if st.button("Calcular"):

    # =============================
    # ICMS
    # =============================

    icms_credito = cmv * icms_credito_perc
    icms_debito = receita * icms_debito_perc
    icms_pagar = icms_debito - icms_credito

    # =============================
    # PIS/COFINS AUTOMÁTICO
    # =============================

    pis_cofins_credito_perc = 0.0925 * (1 - icms_credito_perc)
    pis_cofins_debito_perc = 0.0925 * (1 - icms_debito_perc)

    pis_cofins_credito = cmv * pis_cofins_credito_perc
    pis_cofins_debito = receita * pis_cofins_debito_perc
    pis_cofins_pagar = pis_cofins_debito - pis_cofins_credito

    # =============================
    # Custos Variáveis
    # =============================

    custo_variavel = receita * custos_variaveis_perc

    # =============================
    # Base IRPJ
    # =============================

    base_irpj = (
        receita
        - cmv
        - despesas_dedutiveis
        - icms_pagar
        - pis_cofins_pagar
        - custo_variavel
    )

    # =============================
    # IRPJ
    # =============================

    adicional = max(base_irpj - 20000, 0) * 0.10
    irpj = base_irpj * 0.15 + adicional

    # =============================
    # CSLL
    # =============================

    csll = base_irpj * 0.09

    # =============================
    # Lucro Final
    # =============================

    lucro = (
        receita
        - cmv
        - despesas_gerais
        - icms_pagar
        - pis_cofins_pagar
        - custo_variavel
        - irpj
        - csll
    )

    margem = lucro / receita if receita != 0 else 0

    # =============================
    # Exibição dos resultados
    # =============================

    st.subheader("Resultado")

    st.write("Receita Total:", formatar_moeda(receita))
    st.write("CMV:", formatar_moeda(cmv))

    st.write("ICMS Crédito:", formatar_moeda(icms_credito))
    st.write("ICMS Débito:", formatar_moeda(icms_debito))
    st.write("ICMS a Pagar:", formatar_moeda(icms_pagar))

    st.write("Alíquota PIS/COFINS Crédito:", formatar_percentual(pis_cofins_credito_perc))
    st.write("Alíquota PIS/COFINS Débito:", formatar_percentual(pis_cofins_debito_perc))

    st.write("PIS/COFINS Crédito:", formatar_moeda(pis_cofins_credito))
    st.write("PIS/COFINS Débito:", formatar_moeda(pis_cofins_debito))
    st.write("PIS/COFINS a Pagar:", formatar_moeda(pis_cofins_pagar))

    st.write("Base IRPJ:", formatar_moeda(base_irpj))
    st.write("IRPJ a Pagar:", formatar_moeda(irpj))
    st.write("CSLL a Pagar:", formatar_moeda(csll))

    st.write("Despesas Gerais:", formatar_moeda(despesas_gerais))
    st.write("Custo Variável:", formatar_moeda(custo_variavel))

    st.write("Lucro Final:", formatar_moeda(lucro))
    st.write("Margem Final:", formatar_percentual(margem))

