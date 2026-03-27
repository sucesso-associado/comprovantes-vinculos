import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Carrega a chave de API do arquivo .env
load_dotenv()
CHAVE_API = os.getenv("GEMINI_API_KEY")

# Inicializa o novo cliente oficial do Gemini
client = genai.Client(api_key=CHAVE_API)

def extrair_dados_pdf(arquivo_pdf):
    try:
        # Volta o "ponteiro" do arquivo para o início para garantir a leitura completa
        arquivo_pdf.seek(0)
        pdf_bytes = arquivo_pdf.read()

        # O "Prompt" - O que vamos pedir para a IA fazer
        prompt = """
        Você é um assistente especializado em extração de dados de documentos.
        Leia este documento (Carta de Vínculo/Comprovante) e extraia EXATAMENTE as seguintes informações:
        1. Nome (Nome da pessoa física, geralmente logo no início após 'Eu,')
        2. Razão Social (Nome da empresa representante)
        3. CNPJ (Apenas os números, pontos, traços e barras)
        4. Data (A data de assinatura do documento)
        5. Responsável Rede (Nome de quem assina pela rede ou é citado como responsável no fim do documento)

        Retorne APENAS um objeto JSON válido, com as chaves exatas: 
        "Nome", "Razão Social", "CNPJ", "Data", "Responsável Rede".
        Se não encontrar alguma informação, preencha o valor como null.
        Não adicione nenhuma formatação Markdown, apenas o JSON puro.
        """

        # Envia para o Gemini usando a nova estrutura da biblioteca
        resposta = client.models.generate_content(
            model='gemini-2.5-flash', # Usando o modelo rápido mais atual
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'),
                prompt
            ]
        )
        
        texto_resposta = resposta.text.strip()

        # Limpa possíveis formatações que a IA possa colocar por engano
        if texto_resposta.startswith("```json"):
            texto_resposta = texto_resposta[7:]
        if texto_resposta.startswith("```"):
            texto_resposta = texto_resposta[3:]
        if texto_resposta.endswith("```"):
            texto_resposta = texto_resposta[:-3]

        # Converte a resposta de texto para um Dicionário do Python
        dados_extraidos = json.loads(texto_resposta.strip())
        return dados_extraidos

    except json.JSONDecodeError:
        return {"erro": "A IA retornou um formato inválido. Verifique o documento e tente novamente."}
    except Exception as e:
        return {"erro": f"Falha na extração com IA: {str(e)}"}