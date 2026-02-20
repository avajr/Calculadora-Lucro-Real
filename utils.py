import pandas as pd
import xml.etree.ElementTree as ET

def extrair_dados_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()

    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

    try:

        # 🔑 Chave de acesso
        infNFe = root.find('.//nfe:infNFe', ns)
        chave = infNFe.attrib.get("Id").replace("NFe", "")

        emissao = root.find('.//nfe:dhEmi', ns)
        if emissao is None:
            emissao = root.find('.//nfe:dEmi', ns)

        emissao = pd.to_datetime(emissao.text[:10])

        total = root.find('.//nfe:vNF', ns)
        valor = float(total.text)

        # 🚛 Frete
        frete_tag = root.find('.//nfe:ICMSTot/nfe:vFrete', ns)
        frete = float(frete_tag.text) if frete_tag is not None else 0.0

        cfop = root.find('.//nfe:CFOP', ns)
        cfop = cfop.text if cfop is not None else "N/A"

        # 🏢 Emitente
        cnpj = root.find('.//nfe:emit/nfe:CNPJ', ns)
        razao = root.find('.//nfe:emit/nfe:xNome', ns)

        cnpj = cnpj.text if cnpj is not None else "N/A"
        razao = razao.text if razao is not None else "N/A"

        # 🧾 Destinatário
        cnpj_dest = root.find('.//nfe:dest/nfe:CNPJ', ns)
        razao_dest = root.find('.//nfe:dest/nfe:xNome', ns)

        cnpj_dest = cnpj_dest.text if cnpj_dest is not None else "N/A"
        razao_dest = razao_dest.text if razao_dest is not None else "N/A"

        # Impostos
        def pegar_valor(tag):
            campo = root.find(f'.//nfe:{tag}', ns)
            return float(campo.text) if campo is not None else 0.0

        impostos = {
            "ICMS": pegar_valor("vICMS"),
            "ST": pegar_valor("vST"),
            "PIS": pegar_valor("vPIS"),
            "COFINS": pegar_valor("vCOFINS"),
            "IPI": pegar_valor("vIPI")
        }

        vencimentos = root.findall('.//nfe:dVenc', ns)

        if vencimentos:
            datas_venc = [pd.to_datetime(v.text) for v in vencimentos]
        else:
            datas_venc = [emissao]

        return {
            "chave": chave,
            "emissao": emissao,
            "valor": valor,
            "frete": frete,
            "cfop": cfop,
            "cnpj": cnpj,
            "razao_social": razao,
            "cnpj_destinatario": cnpj_dest,
            "razao_destinatario": razao_dest,
            "vencimentos": datas_venc,
            "impostos": impostos
        }

    except:
        return None


def calcular_defasagem_meses(emissao, vencimento):
    return (vencimento.year - emissao.year) * 12 + (vencimento.month - emissao.month)
