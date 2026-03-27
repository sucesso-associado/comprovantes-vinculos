import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carrega a chave de API
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")

# Inicializa o cliente oficial do Gemini
client = genai.Client(api_key=CHAVE_API)

def extrair_dados_pdf(arquivo_pdf):
    try:
        arquivo_pdf.seek(0)
        pdf_bytes = arquivo_pdf.read()

        # Novo Prompt pedindo os Responsáveis em formato de LISTA
        prompt = """
        Você é um assistente especializado em extração de dados de documentos.
        Leia este documento (Carta de Vínculo/Comprovante) e extraia EXATAMENTE as seguintes informações:
        1. Nome (Nome da pessoa física, geralmente logo no início após 'Eu,')
        2. Razão Social (Nome da empresa representante)
        3. CNPJ (Apenas os números, pontos, traços e barras)
        4. Data (A data de assinatura do documento)
        5. Responsáveis Rede (Uma LISTA com TODOS os nomes de quem assina pela rede ou são citados como responsáveis no fim do documento. Ex: ["João da Silva", "Maria Souza"]).

        Retorne APENAS um objeto JSON válido, com as chaves exatas: 
        "Nome", "Razão Social", "CNPJ", "Data", "Responsáveis Rede".
        Se não encontrar alguma informação, preencha o valor como null (ou uma lista vazia [] no caso dos responsáveis).
        Não adicione nenhuma formatação Markdown, apenas o JSON puro.
        """

        # Mantive o modelo que você testou e deu certo
        resposta = client.models.generate_content(
            model='gemini-2.5-flash-lite', 
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
                prompt
            ]
        )
        
        texto_resposta = resposta.text.strip()

        # Limpeza do JSON
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta[7:]
        if texto_resposta.startswith("```"):
            texto_resposta = texto_resposta[3:]
        if texto_resposta.endswith("```"):
            texto_resposta = texto_resposta[:-3]

        dados_extraidos = json.loads(texto_resposta.strip())
        return dados_extraidos

    except json.JSONDecodeError:
        return {"erro": "A IA retornou um formato inválido. Verifique o documento e tente novamente."}
    except Exception as e:
        return {"erro": f"Falha na extração com IA: {str(e)}"}
