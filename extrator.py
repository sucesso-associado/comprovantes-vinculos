import os
import re
import json
import base64
import fitz  # PyMuPDF
from openai import OpenAI

def pdf_para_base64_png(pdf_source):
    """Converte a primeira página do PDF para uma imagem PNG em Base64."""
    if isinstance(pdf_source, str) and os.path.exists(pdf_source):
        doc = fitz.open(pdf_source)
    else:
        doc = fitz.open(stream=pdf_source, filetype="pdf")
    
    pagina = doc[0]
    pix = pagina.get_pixmap(dpi=150) # Gera a imagem da página
    img_bytes = pix.tobytes("png")
    doc.close()
    
    return base64.b64encode(img_bytes).decode("utf-8")

def extrair_dados_pdf(pdf_source):
    texto_extraido = ""
    
    # 1. Tenta extrair texto nativo primeiro (mais rápido)
    try:
        if isinstance(pdf_source, str) and os.path.exists(pdf_source):
            doc = fitz.open(pdf_source)
            for page in doc:
                texto_extraido += page.get_text()
            doc.close()
        elif isinstance(pdf_source, bytes):
            doc = fitz.open(stream=pdf_source, filetype="pdf")
            for page in doc:
                texto_extraido += page.get_text()
            doc.close()
    except Exception as e:
        print(f"Erro ao tentar ler texto nativo: {e}")

    api_key = os.getenv("NVIDIA_API_KEY")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    # 2. SE FOR PDF DIGITALIZADO (Sem texto): Usa o Nemotron OCR v2 (Multimodal)
    if len(texto_extraido.strip()) < 30:
        try:
            base64_image = pdf_para_base64_png(pdf_source)
            
            prompt_ocr = """Extraia estritamente em formato JSON válido as seguintes informações da imagem deste documento:
            {
              "CNPJ": "CNPJ da empresa (apenas números)",
              "Razão Social": "Razão Social da empresa",
              "Nome": "Nome do Sócio/Proprietário/Outorgante",
              "Data do Doc.": "Data do documento (DD/MM/AAAA)",
              "Responsável Rede": "Nome do Presidente/Diretor/Responsável"
            }
            Retorne APENAS o JSON sem formatação adicional ou explicações."""

            response = client.chat.completions.create(
                model="nvidia/nemotron-ocr-v2", # Modelo para extração visual
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_ocr},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=1024,
                temperature=0.1
            )
            
            conteudo = response.choices[0].message.content.strip()
            
        except Exception as e:
            return {"erro": f"Erro no Nemotron OCR v2: {str(e)}"}

    # 3. SE FOR PDF NATIVO: Usa o Nemotron 3 Ultra (Texto)
    else:
        prompt_texto = f"""Extraia estritamente em formato JSON válido as informações do texto abaixo:
        - "CNPJ"
        - "Razão Social"
        - "Nome"
        - "Data do Doc."
        - "Responsável Rede"

        Texto:
        {texto_extraido}"""

        try:
            response = client.chat.completions.create(
                model="nvidia/nemotron-3-ultra-550b-a55b",
                messages=[{"role": "user", "content": prompt_texto}],
                temperature=0.1,
                max_tokens=1024
            )
            conteudo = response.choices[0].message.content.strip()
        except Exception as e:
            return {"erro": f"Erro no Nemotron Text API: {str(e)}"}

    # Processa o retorno em JSON
    try:
        if conteudo.startswith("```"):
            conteudo = re.sub(r"^```(?:json)?\n", "", conteudo)
            conteudo = re.sub(r"\n```$", "", conteudo)

        dados = json.loads(conteudo)
        return dados
    except Exception as e:
        return {"erro": f"Falha ao interpretar retorno da NVIDIA: {conteudo}"}
