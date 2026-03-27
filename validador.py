import pandas as pd
import re
import requests
import io

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vStbYGz6Lq-6ZBrCawbKxItY-OzTTLABh-iS1efLY5WZgREDNeJNkH9J23peyde89H7lzzm8tPYQymA/pub?output=csv"

def limpar_cnpj(cnpj):
    if not isinstance(cnpj, str): cnpj = str(cnpj)
    return re.sub(r'[^0-9]', '', cnpj)

def validar_com_planilha(dados_pdf):
    if not dados_pdf.get("CNPJ"): 
        return {"erro": "Sem CNPJ para validar."}
        
    try:
        # --- A MÁGICA NOVA AQUI ---
        # 1. Fazemos o download blindado da planilha usando requests
        resposta = requests.get(URL_PLANILHA)
        if resposta.status_code != 200:
            return {"erro": f"Falha ao acessar a planilha online. Status: {resposta.status_code}"}
        
        # 2. Lemos o texto baixado como se fosse um arquivo pro Pandas não se perder
        df = pd.read_csv(io.StringIO(resposta.text))
        # ---------------------------
        
        cnpj_busca = limpar_cnpj(dados_pdf["CNPJ"])
        df['CNPJ_Limpo'] = df['CNPJ'].apply(limpar_cnpj)
        
        linha = df[df['CNPJ_Limpo'] == cnpj_busca]
        
        if linha.empty: 
            return {"status": "Não Encontrado", "mensagem": "CNPJ não localizado na planilha da base de dados."}
        
        linha = linha.iloc[0]
        checklist = {}
        divergencias = 0
        
        def pegar_valor(coluna):
            valor = linha.get(coluna)
            return "" if pd.isna(valor) else str(valor).strip()

        # 1. Validar Nome x Proprietário
        nome_pdf = str(dados_pdf.get("Nome", "")).upper().strip()
        nome_planilha = pegar_valor("Proprietário").upper()
        ok_nome = (nome_pdf in nome_planilha) or (nome_planilha in nome_pdf) if nome_pdf and nome_planilha else False
        checklist["Proprietário"] = {"ok": ok_nome, "pdf": dados_pdf.get("Nome"), "planilha": pegar_valor("Proprietário")}
        if not ok_nome: divergencias += 1
            
        # 2. Validar Razão Social
        razao_pdf = str(dados_pdf.get("Razão Social", "")).upper().strip()
        razao_planilha = pegar_valor("Razão Social").upper()
        ok_razao = (razao_pdf in razao_planilha) or (razao_planilha in razao_pdf) if razao_pdf and razao_planilha else False
        checklist["Razão Social"] = {"ok": ok_razao, "pdf": dados_pdf.get("Razão Social"), "planilha": pegar_valor("Razão Social")}
        if not ok_razao: divergencias += 1
            
        # 3. Validar Responsáveis Rede
        responsaveis_pdf = dados_pdf.get("Responsáveis Rede", [])
        
        if isinstance(responsaveis_pdf, str):
            responsaveis_pdf = [responsaveis_pdf]
        elif not isinstance(responsaveis_pdf, list):
            responsaveis_pdf = []

        lista_pdf_limpa = [str(nome).upper().strip() for nome in responsaveis_pdf if nome]
        resp_planilha = pegar_valor("Responsáveis Rede").upper()

        ok_resp = False
        for nome_pdf in lista_pdf_limpa:
            if nome_pdf in resp_planilha:
                ok_resp = True
                break

        texto_pdf_tela = ", ".join([str(n).title() for n in responsaveis_pdf if n]) if responsaveis_pdf else "Nenhum encontrado"
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
