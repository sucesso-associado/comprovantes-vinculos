import requests
import re
import time

def consultar_cnpj_receitaws(cnpj):
    if not cnpj:
        return {"erro": "CNPJ não fornecido."}

    cnpj_limpo = re.sub(r'[^0-9]', '', cnpj)
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
    
    try:
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            dados = resposta.json()
            if dados.get('status') == 'ERROR':
                return {"erro": dados.get('message', 'CNPJ inválido.')}
                
            return {
                "Razão Social": dados.get("nome"),
                "Situação": dados.get("situacao"),
                "CNAE": dados.get("atividade_principal", [{}])[0].get("code"),
                "Atividade": dados.get("atividade_principal", [{}])[0].get("text"),
                "Endereço": f"{dados.get('logradouro')}, {dados.get('numero')} - {dados.get('bairro')}, {dados.get('municipio')}/{dados.get('uf')}"
            }
        elif resposta.status_code == 429:
            return {"erro": "Muitas consultas à ReceitaWS. Aguarde 1 minuto e tente novamente."}
        else:
            return {"erro": "Erro na API da Receita Federal."}
    except Exception as e:
        return {"erro": f"Falha na conexão: {str(e)}"}