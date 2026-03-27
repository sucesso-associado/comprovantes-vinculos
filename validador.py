import pandas as pd
import re
import requests
import io

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vStbYGz6Lq-6ZBrCawbKxItY-OzTTLABh-iS1efLY5WZgREDNeJNkH9J23peyde89H7lzzm8tPYQymA/pub?output=csv"

def limpar_cnpj(cnpj):
    # Garante que seja string e remove tudo o que não for número
    if not isinstance(cnpj, str): cnpj = str(cnpj)
    return re.sub(r'[^0-9]', '', cnpj)

def validar_com_planilha(dados_pdf):
    if not dados_pdf.get("CNPJ"): 
        return {"erro": "Sem CNPJ para validar."}
        
    try:
        # --- BLINDAGEM COMPLETA AQUI ---
        # 1. Buscamos a planilha (requests)
        resposta = requests.get(URL_PLANILHA)
        if resposta.status_code != 200:
            return {"erro": f"Falha ao acessar a planilha online. Status: {resposta.status_code}"}
        
        # 2. Forçamos a codificação UTF-8
        resposta.encoding = 'utf-8'

        # 3. LEMOS O TEXTO E FORÇAMOS A COLUNA 'CNPJ' A SER TEXTO (str)
        # Isso impede que o Pandas converta para número e apague os zeros à esquerda!
        df = pd.read_csv(io.StringIO(resposta.text), dtype={'CNPJ': str}) # <--- A LINHA SALVADORA
        # -------------------------------
        
        # Ajuste de segurança: Remove espaços extras dos nomes das colunas
        df.columns = df.columns.str.strip()
        
        # Limpa o CNPJ que veio do PDF (ex: mantém o zero)
        cnpj_busca = limpar_cnpj(dados_pdf["CNPJ"])
        
        # Limpa o CNPJ da planilha (que agora garantimos ter o zero)
        df['CNPJ_Limpo'] = df['CNPJ'].apply(limpar_cnpj)
        
        # Realiza a busca
        linha = df[df['CNPJ_Limpo'] == cnpj_busca]
        
        if linha.empty: 
            return {"status": "Não Encontrado", "mensagem": "CNPJ não localizado na planilha da base de dados."}
        
        linha = linha.iloc[0]
        checklist = {}
        divergencias = 0
        
        def pegar_valor(coluna):
            # Procura a coluna ignorando maiúsculas/minúsculas
            coluna_real = next((c for c in df.columns if c.upper() == coluna.upper()), None)
            if not coluna_real: return ""
            valor = linha.get(coluna_real)
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
        if isinstance(responsaveis_pdf, str): responsaveis_pdf = [responsaveis_pdf]
        elif not isinstance(responsaveis_pdf, list): responsaveis_pdf = []

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
