# =====================================================
# 🏢 AGREGAÇÃO POR CLIENTE (XML SAÍDA)
# =====================================================

st.divider()
st.subheader("🏢 Agregador por Cliente (Saídas XML)")

receita_cliente = (
    df[df["tipo_operacao"] == "Saída"]  # só Saída, exclui Outros
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
    df[df["tipo_operacao"] == "Entrada"]  # só Entrada, exclui Outros
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
