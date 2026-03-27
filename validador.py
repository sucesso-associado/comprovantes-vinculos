import pandas as pd
import re
import requests
import io
import unicodedata
import os
from dotenv import load_dotenv

# Carrega as variáveis do cofre (Secrets do Streamlit ou .env local)
load_dotenv()

URL_PLANILHA = os.getenv("URL_PLANILHA")

def limpar_cnpj(cnpj):
    if not isinstance(cnpj, str): cnpj = str(cnpj)
    return re.sub(r'[^0-9]', '', cnpj)

def padronizar_texto(texto):
    """Remove acentos, espaços extras e deixa tudo em maiúsculo para comparação segura."""
    if not texto or pd.isna(texto): 
        return ""
    # Transforma em texto, tira espaços das pontas e deixa maiúsculo
    texto = str(texto).strip().upper()
    # Remove os acentos magicamente
    texto_sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto_sem_acento

def validar_com_planilha(dados_pdf):
    if not dados_pdf.get("CNPJ"): 
        return {"erro": "Sem CNPJ para validar."}
        
    try:
        resposta = requests.get(URL_PLANILHA)
        if resposta.status_code != 200:
            return {"erro": f"Falha ao acessar a planilha online. Status: {resposta.status_code}"}
        
        resposta.encoding = 'utf-8'

        df = pd.read_csv(io.StringIO(resposta.text), dtype={'CNPJ': str})
        df.columns = df.columns.str.strip()
        
        cnpj_busca = limpar_cnpj(dados_pdf["CNPJ"])
        df['CNPJ_Limpo'] = df['CNPJ'].apply(limpar_cnpj)
        
        linha = df[df['CNPJ_Limpo'] == cnpj_busca]
        
        if linha.empty: 
            return {"status": "Não Encontrado", "mensagem": "CNPJ não localizado na planilha da base de dados."}
        
        linha = linha.iloc[0]
        checklist = {}
        divergencias = 0
        
        def pegar_valor(coluna):
            coluna_real = next((c for c in df.columns if c.upper() == coluna.upper()), None)
            if not coluna_real: return ""
            valor = linha.get(coluna_real)
            return "" if pd.isna(valor) else str(valor).strip()

        # 1. Validar Nome x Proprietário (Usando a nova padronização)
        nome_pdf_limpo = padronizar_texto(dados_pdf.get("Nome", ""))
        nome_plan_limpo = padronizar_texto(pegar_valor("Proprietário"))
        
        ok_nome = (nome_pdf_limpo in nome_plan_limpo) or (nome_plan_limpo in nome_pdf_limpo) if nome_pdf_limpo and nome_plan_limpo else False
        checklist["Proprietário"] = {"ok": ok_nome, "pdf": dados_pdf.get("Nome") or "-", "planilha": pegar_valor("Proprietário")}
        if not ok_nome: divergencias += 1
            
        # 2. Validar Razão Social (Usando a nova padronização)
        razao_pdf_limpo = padronizar_texto(dados_pdf.get("Razão Social", ""))
        razao_plan_limpo = padronizar_texto(pegar_valor("Razão Social"))
        
        ok_razao = (razao_pdf_limpo in razao_plan_limpo) or (razao_plan_limpo in razao_pdf_limpo) if razao_pdf_limpo and razao_plan_limpo else False
        checklist["Razão Social"] = {"ok": ok_razao, "pdf": dados_pdf.get("Razão Social") or "-", "planilha": pegar_valor("Razão Social")}
        if not ok_razao: divergencias += 1
            
        # 3. Validar Responsáveis Rede (Usando a nova padronização)
        responsaveis_pdf = dados_pdf.get("Responsáveis Rede", [])
        if isinstance(responsaveis_pdf, str): responsaveis_pdf = [responsaveis_pdf]
        elif not isinstance(responsaveis_pdf, list): responsaveis_pdf = []

        # Limpa todos os nomes da lista do PDF
        lista_pdf_limpa = [padronizar_texto(nome) for nome in responsaveis_pdf if nome]
        resp_plan_limpo = padronizar_texto(pegar_valor("Responsáveis Rede"))

        ok_resp = False
        for nome_pdf_limpo in lista_pdf_limpa:
            if nome_pdf_limpo in resp_plan_limpo:
                ok_resp = True
                break

        texto_pdf_tela = ", ".join([str(n) for n in responsaveis_pdf if n]) if responsaveis_pdf else "Nenhum encontrado"
        texto_planilha_tela = pegar_valor("Responsáveis Rede")

        checklist["Responsáveis pela Rede"] = {
            "ok": ok_resp, 
            "pdf": texto_pdf_tela, 
            "planilha": texto_planilha_tela
        }
        if not ok_resp: divergencias += 1

        status_final = "Aprovado" if divergencias == 0 else "Divergente"
        return {"status": status_final, "checklist": checklist}

    except Exception as e:
        return {"erro": f"Erro ao processar planilha: {str(e)}"}
