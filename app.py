import streamlit as st
import requests
import io
from extrator import extrair_dados_pdf
from receita_api import consultar_cnpj_receitaws
from validador import validar_com_planilha

st.set_page_config(page_title="Validador de Vínculos", layout="wide")

st.title("📄 Comprovantes de Vínculos - Validator")
st.write("Faça o upload ou cole o link da carta para extrair os dados e auditar automaticamente.")

aba1, aba2 = st.tabs(["📂 Fazer Upload", "🔗 Inserir Link"])
arquivo_pdf = None

with aba1:
    arquivo_upload = st.file_uploader("Arraste o PDF aqui", type=["pdf"])
    if arquivo_upload is not None: arquivo_pdf = arquivo_upload

with aba2:
    url_pdf = st.text_input("Cole o link público do PDF aqui:")
    if url_pdf:
        with st.spinner("Baixando PDF..."):
            try:
                resposta = requests.get(url_pdf)
                if resposta.status_code == 200:
                    arquivo_pdf = io.BytesIO(resposta.content)
                    st.success("PDF carregado!")
                else: st.error("Erro ao acessar o link.")
            except Exception as e: st.error(f"Falha: {str(e)}")

st.divider()

if arquivo_pdf is not None:
    if st.button("🚀 Processar e Validar Tudo", use_container_width=True):
        
        with st.spinner("Lendo o PDF com Inteligência Artificial..."):
            dados_pdf = extrair_dados_pdf(arquivo_pdf)
        
        if "erro" in dados_pdf:
            st.error(dados_pdf["erro"])
        else:
            st.subheader("📑 1. Dados Lidos do Documento")
            c1, c2, c3 = st.columns(3)
            c1.metric("CNPJ", dados_pdf.get("CNPJ", "-"))
            c2.metric("Data do Doc.", dados_pdf.get("Data", "-"))
            
            # TRATAMENTO PARA A LISTA DE RESPONSÁVEIS NA TELA
            resp_lista = dados_pdf.get("Responsáveis Rede", [])
            if isinstance(resp_lista, list):
                resp_texto = ", ".join([str(n) for n in resp_lista if n]) if resp_lista else "-"
            else:
                resp_texto = str(resp_lista)
                
            c3.metric("Responsáveis", resp_texto)
            
            st.write(f"**Nome:** {dados_pdf.get('Nome')}")
            st.write(f"**Razão Social:** {dados_pdf.get('Razão Social')}")
            
            st.divider()
            st.subheader("📋 2. Relatório de Auditoria")
            
            col_receita, col_planilha = st.columns(2)
            
            with col_receita:
                st.markdown("#### 🏛️ Receita Federal")
                with st.spinner("Consultando CNPJ..."):
                    dados_receita = consultar_cnpj_receitaws(dados_pdf.get("CNPJ"))
                
                if "erro" in dados_receita:
                    st.error(dados_receita["erro"])
                else:
                    situacao = dados_receita.get("Situação", "")
                    if situacao == "ATIVA":
                        st.success(f"✅ **CNPJ ATIVO**")
                    else:
                        st.error(f"❌ **CNPJ {situacao}**")
                    
                    st.write(f"**Razão Social Oficial:** {dados_receita.get('Razão Social')}")
                    st.write(f"**Atividade (CNAE):** {dados_receita.get('CNAE')} - {dados_receita.get('Atividade')}")
                    st.caption(f"📍 {dados_receita.get('Endereço')}")

            with col_planilha:
                st.markdown("#### 📊 Base de Dados (Planilha)")
                with st.spinner("Cruzando dados..."):
                    resultado_validacao = validar_com_planilha(dados_pdf)
                
                if "erro" in resultado_validacao:
                    st.error(resultado_validacao["erro"])
                elif resultado_validacao.get("status") == "Não Encontrado":
                    st.warning(f"⚠️ {resultado_validacao['mensagem']}")
                else:
                    checklist = resultado_validacao.get("checklist", {})
                    
                    for campo, info in checklist.items():
                        icone = "✅" if info["ok"] else "❌"
                        st.markdown(f"**{icone} {campo}**")
                        st.markdown(f"> 📄 **No PDF:** {info['pdf']}  \n> 🗂️ **Na Planilha:** {info['planilha']}")
                    
                    st.write("") 
                    if resultado_validacao["status"] == "Aprovado":
                        st.success("🎉 **TUDO CERTO!** Os dados batem perfeitamente com a planilha interna.")
                    else:
                        st.error("⚠️ **DIVERGÊNCIA!** Verifique os campos marcados com ❌ acima.")
