import pandas as pd
import re

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vStbYGz6Lq-6ZBrCawbKxItY-OzTTLABh-iS1efLY5WZgREDNeJNkH9J23peyde89H7lzzm8tPYQymA/pub?output=csv"

def limpar_cnpj(cnpj):
    if not isinstance(cnpj, str): cnpj = str(cnpj)
    return re.sub(r'[^0-9]', '', cnpj)

def validar_com_planilha(dados_pdf):
    if not dados_pdf.get("CNPJ"): 
        return {"erro": "Sem CNPJ para validar."}
        
    try:
        df = pd.read_csv(URL_PLANILHA)
        cnpj_busca = limpar_cnpj(dados_pdf["CNPJ"])
        df['CNPJ_Limpo'] = df['CNPJ'].apply(limpar_cnpj)
        
        linha = df[df['CNPJ_Limpo'] == cnpj_busca]
        
        if linha.empty: 
            return {"status": "Não Encontrado", "mensagem": "CNPJ não localizado na planilha da base de dados."}
        
        linha = linha.iloc[0]
        checklist = {}
        divergencias = 0
        
        # Função auxiliar para limpar NaN da planilha
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
            
        # 3. Validar Responsável Rede
        resp_pdf = str(dados_pdf.get("Responsável Rede", "")).upper().strip()
        resp_planilha = pegar_valor("Responsáveis Rede").upper()
        ok_resp = (resp_pdf in resp_planilha) or (resp_planilha in resp_pdf) if resp_pdf and resp_planilha else False
        checklist["Responsável pela Rede"] = {"ok": ok_resp, "pdf": dados_pdf.get("Responsável Rede"), "planilha": pegar_valor("Responsáveis Rede")}
        if not ok_resp: divergencias += 1

        status_final = "Aprovado" if divergencias == 0 else "Divergente"
        return {"status": status_final, "checklist": checklist}

    except Exception as e:
        return {"erro": f"Erro ao processar planilha: {str(e)}"}