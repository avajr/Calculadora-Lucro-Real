import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Simulador de Lucro Real/Presumido", layout="wide")
st.title("💰 Simulador Regime Tributário")

# =============================
# Funções de formatação
# =============================
def formatar_moeda(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor, casas=3):
    return f"{valor*100:,.{casas}f}%".replace(",", "X").replace(".", ",").replace("X", ".")

# =============================
# Entradas do Usuário
# =============================
st.header("📊 Dados da Operação")
col1, col2 = st.columns(2)

with col1:
    regime = st.selectbox("Regime Tributário", ["Lucro Real", "Lucro Presumido"])
    receita = st.number_input("Receita Bruta", value=0.0, step=1000.0)
    cmv = st.number_input("CMV", value=0.0, step=1000.0)
    custos_variaveis = st.number_input("Custos Variáveis", value=0.0, step=1000.0)

with col2:
    icms_credito_perc = st.number_input("Crédito ICMS (%)", value=0.0, step=0.00001)
    icms_debito_perc = st.number_input("Débito ICMS (%)", value=0.0, step=0.00001)
    despesas_gerais = st.number_input("Despesas Gerais", value=0.0, step=1000.0)

# Ajuste para comparador
if regime == "Lucro Real" or st.checkbox("💡 Incluir Despesas Dedutíveis para Comparador"):
    despesas_dedutiveis = st.number_input("Despesas Dedutíveis IRPJ", value=0.0, step=1000.0)
else:
    despesas_dedutiveis = 0.0

comparador = st.checkbox("📊 Ativar Comparador (Lucro Real vs Presumido)")

# =============================
# Função para cálculo
# =============================
def calcular_lucro(receita, cmv, icms_credito_perc, icms_debito_perc,
                   despesas_dedutiveis, despesas_gerais, custos_variaveis,
                   regime):
    
    icms_credito_perc /= 100
    icms_debito_perc /= 100
    
    icms_credito = cmv * icms_credito_perc
    icms_debito = receita * icms_debito_perc
    icms_pagar = icms_debito - icms_credito
    
    if regime == "Lucro Real":
        pis_cofins_credito_perc = 0.0925 * (1 - icms_credito_perc)
        pis_cofins_debito_perc = 0.0925 * (1 - icms_debito_perc)
        pis_cofins_credito = cmv * pis_cofins_credito_perc
        pis_cofins_debito = receita * pis_cofins_debito_perc
        pis_cofins_pagar = pis_cofins_debito - pis_cofins_credito
        base_irpj = receita - cmv - despesas_dedutiveis - icms_pagar - pis_cofins_pagar - custos_variaveis
        adicional = max(base_irpj - 20000, 0) * 0.10
        irpj = base_irpj * 0.15 + adicional
        csll = base_irpj * 0.09
    else:
        base_presumida = receita * 0.08
        adicional = max(base_presumida - 20000, 0) * 0.10
        irpj = base_presumida * 0.15 + adicional
        csll = receita * 0.12 * 0.09
        pis_cofins_pagar = receita * (1 - icms_debito_perc) * 0.0365
    
    lucro = receita - cmv - despesas_gerais - icms_pagar - pis_cofins_pagar - custos_variaveis - irpj - csll
    margem = lucro / receita if receita != 0 else 0
    carga_tributaria = (icms_pagar + pis_cofins_pagar + irpj + csll) / receita if receita != 0 else 0
    
    return {
        "💳 ICMS Crédito": icms_credito,
        "💸 ICMS Débito": icms_debito,
        "🧾 ICMS a Pagar": icms_pagar,
        "📈 PIS/COFINS a Pagar": pis_cofins_pagar,
        "🏦 IRPJ a Pagar": irpj,
        "🏛️ CSLL a Pagar": csll,
        "💰 Lucro Final": lucro,
        "📊 Margem": margem,
        "⚖️ Carga Tributária": carga_tributaria
    }

# =============================
# Função de exibição de card com azul
# =============================
def exibir_card(resultados, titulo, cor="#D0E1F9"):
    html = f"""
        <div style='padding:15px; border-radius:10px; background-color:{cor}; color:#0B1D3D;'>
            <h3>{titulo}</h3>
            <p>💰 Lucro Final: {formatar_moeda(resultados['💰 Lucro Final'])}</p>
            <p>📊 Margem: {formatar_percentual(resultados['📊 Margem'])}</p>
            <p>⚖️ Carga Tributária: {formatar_percentual(resultados['⚖️ Carga Tributária'])}</p>
            <hr style='border:1px solid #ccc'>
            <p>💳 ICMS Crédito: {formatar_moeda(resultados['💳 ICMS Crédito'])}</p>
            <p>💸 ICMS Débito: {formatar_moeda(resultados['💸 ICMS Débito'])}</p>
            <p>🧾 ICMS a Pagar: {formatar_moeda(resultados['🧾 ICMS a Pagar'])}</p>
            <p>📈 PIS/COFINS a Pagar: {formatar_moeda(resultados['📈 PIS/COFINS a Pagar'])}</p>
            <p>🏦 IRPJ a Pagar: {formatar_moeda(resultados['🏦 IRPJ a Pagar'])}</p>
            <p>🏛️ CSLL a Pagar: {formatar_moeda(resultados['🏛️ CSLL a Pagar'])}</p>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# =============================
# Cálculo e exibição
# =============================
if st.button("Calcular"):

    st.markdown(f"<h2 style='color:#1f77b4;'>💵 Receita Total: {formatar_moeda(receita)}</h2>", unsafe_allow_html=True)
    
    if comparador:
        resultados_real = calcular_lucro(receita, cmv, icms_credito_perc, icms_debito_perc,
                                        despesas_dedutiveis, despesas_gerais, custos_variaveis,
                                        "Lucro Real")
        resultados_presumido = calcular_lucro(receita, cmv, icms_credito_perc, icms_debito_perc,
                                             despesas_dedutiveis, despesas_gerais, custos_variaveis,
                                             "Lucro Presumido")
        
        st.subheader("📊 Comparador de Regimes")
        col_real, col_pres = st.columns(2)
        
        with col_real:
            exibir_card(resultados_real, "💎 Lucro Real", "#1F4E79")
        with col_pres:
            exibir_card(resultados_presumido, "💎 Lucro Presumido", "#85C1E9")
        
        # Gráfico comparativo de tributos
        tributos = ["🧾 ICMS a Pagar", "📈 PIS/COFINS a Pagar", "🏦 IRPJ a Pagar", "🏛️ CSLL a Pagar"]
        df_tributos = pd.DataFrame({
            "Tributo": tributos,
            "Lucro Real": [resultados_real[t] for t in tributos],
            "Lucro Presumido": [resultados_presumido[t] for t in tributos]
        })
        fig = go.Figure(data=[
            go.Bar(name='Lucro Real', x=df_tributos['Tributo'], y=df_tributos['Lucro Real'], marker_color='#1F4E79'),
            go.Bar(name='Lucro Presumido', x=df_tributos['Tributo'], y=df_tributos['Lucro Presumido'], marker_color='#85C1E9')
        ])
        fig.update_layout(barmode='group', title="📊 Comparação de Tributos", yaxis_title="Valor (R$)")
        st.plotly_chart(fig, use_container_width=True)
        
        if resultados_real["💰 Lucro Final"] > resultados_presumido["💰 Lucro Final"]:
            st.success("✅ Regime mais viável: Lucro Real")
        elif resultados_presumido["💰 Lucro Final"] > resultados_real["💰 Lucro Final"]:
            st.success("✅ Regime mais viável: Lucro Presumido")
        else:
            st.info("ℹ️ Ambos os regimes geram o mesmo lucro")
        
    else:
        resultados = calcular_lucro(receita, cmv, icms_credito_perc, icms_debito_perc,
                                    despesas_dedutiveis, despesas_gerais, custos_variaveis,
                                    regime)
        st.subheader(f"📈 Resultado - {regime}")
        exibir_card(resultados, f"💎 {regime}", "#1F4E79" if regime=="Lucro Real" else "#85C1E9")
        
        # Gráfico para regime único
        tributos = ["🧾 ICMS a Pagar", "📈 PIS/COFINS a Pagar", "🏦 IRPJ a Pagar", "🏛️ CSLL a Pagar"]
        df_tributos = pd.DataFrame({
            "Tributo": tributos,
            "Valor": [resultados[t] for t in tributos]
        })
        fig = go.Figure(data=[
            go.Bar(x=df_tributos['Tributo'], y=df_tributos['Valor'], marker_color='#1F4E79')
        ])
        fig.update_layout(title=f"📊 Tributos - {regime}", yaxis_title="Valor (R$)")
        st.plotly_chart(fig, use_container_width=True)

