import os
import re
import io
import json
import pymupdf  # Importação atualizada recomendada
import pypdf
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

client_nvidia = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

def normalize_cnpj(cnpj_str):
    if not isinstance(cnpj_str, str): 
        return ""
    return re.sub(r'\D', '', cnpj_str).strip()

def limpar_e_converter_json(texto):
    """Garante a extração do objeto JSON da resposta da IA."""
    if not texto:
        return None
    try:
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"Erro ao converter JSON: {e}")
    return None

def extrair_texto_pdf(pdf_bytes):
    """Extrai todo o texto contido no PDF usando PyMuPDF/pypdf."""
    texto = ""
    # Tentativa 1: PyMuPDF (rápido e preciso)
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            texto += page.get_text() or ""
        doc.close()
    except Exception as e:
        print(f"Erro ao ler via PyMuPDF: {e}")

    # Tentativa 2: pypdf (fallback)
    if not texto.strip():
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
            for page in reader.pages:
                texto += page.extract_text() or ""
        except Exception as e:
            print(f"Erro ao ler via pypdf: {e}")

    return texto

def estruturar_dados_com_nemotron(texto_documento):
    """Envia apenas o TEXTO extraído para o Nemotron estruturar em JSON."""
    try:
        prompt = f"""
        Você é um extrator de dados de documentos extremamente preciso.
        Análise o seguinte texto extraído de um comprovante/carta de vínculo:

        --- INÍCIO DO TEXTO ---
        {texto_documento}
        --- FIM DO TEXTO ---

        Extraia EXATAMENTE estas informações:
        1. Nome: Nome do representante legal (geralmente após "Eu," ou no início da qualificação da pessoa física).
        2. Razão Social: Nome da empresa/farmácia representada.
        3. CNPJ: Apenas os números do CNPJ da empresa (14 dígitos).
        4. Data: A data do documento no formato DD/MM/AAAA.
        5. Responsável Rede: Nome do responsável citado no documento ou que assina pela rede.

        Responda APENAS um objeto JSON válido, sem explicações ou Markdown, no seguinte formato:
        {{
            "Nome": "string ou null",
            "Razão Social": "string ou null",
            "CNPJ": "string ou null",
            "Data": "string ou null",
            "Responsável Rede": "string ou null"
        }}
        """

        completion = client_nvidia.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            stream=False
        )

        texto_resposta = completion.choices[0].message.content or ""
        return limpar_e_converter_json(texto_resposta)
    except Exception as e:
        print(f"Erro ao estruturar com Nemotron: {e}")
        return None

def extrair_dados_pdf(arquivo_pdf):
    """Função principal chamada pelo app.py."""
    try:
        if hasattr(arquivo_pdf, 'seek'):
            arquivo_pdf.seek(0)
            pdf_bytes = arquivo_pdf.read()
        else:
            pdf_bytes = arquivo_pdf

        if not NVIDIA_API_KEY:
            return {"erro": "Chave NVIDIA_API_KEY não configurada no arquivo .env"}

        # 1. Extrai o texto do PDF via código (sem enviar imagem para a API)
        texto_documento = extrair_texto_pdf(pdf_bytes)

        if not texto_documento.strip():
            return {"erro": "O PDF está em formato de imagem/digitalizado sem camada de texto editável."}

        # 2. Envia apenas a string de texto para o Nemotron organizar o JSON
        dados = estruturar_dados_com_nemotron(texto_documento)

        if not dados or not isinstance(dados, dict):
            return {"erro": "O Nemotron da NVIDIA não conseguiu estruturar os dados do documento."}

        # Trata a formatação do CNPJ
        if dados.get("CNPJ"):
            dados["CNPJ"] = normalize_cnpj(dados["CNPJ"])

        return dados

    except Exception as e:
        return {"erro": f"Falha no processamento NVIDIA: {str(e)}"}