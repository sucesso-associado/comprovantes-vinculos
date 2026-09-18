import pandas as pd
import re

ID_PLANILHA = "1-1uuDbFa_M3aAeXj-NAyKkI8bxPw42rY4ktRrtYtPRA"

# GIDs das abas
GID_LOJAS = "805952313"
GID_USUARIOS = "478021459"  # Ajuste com o GID exato da sua aba USUÁRIOS se for diferente

URL_LOJAS = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid={GID_LOJAS}"
URL_USUARIOS = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv&gid={GID_USUARIOS}"

def limpar_cnpj(cnpj):
    """Limpa o CNPJ mantendo apenas números e preenche com zeros até 14 dígitos."""
    if not isinstance(cnpj, str): 
        cnpj = str(cnpj)
    apenas_numeros = re.sub(r'[^0-9]', '', cnpj)
    if not apenas_numeros:
        return ""
    return apenas_numeros.zfill(14)

def normalizar_texto(texto):
    if pd.isna(texto) or not texto:
        return ""
    txt = str(texto).strip().upper()
    return re.sub(r'\s+', ' ', txt)

def validar_com_planilha(dados_pdf):
    if not dados_pdf.get("CNPJ"): 
        return {"erro": "Sem CNPJ para validar."}
        
    try:
        # Carrega a aba LOJAS
        df_lojas = pd.read_csv(URL_LOJAS, dtype=str)
        df_lojas.columns = df_lojas.columns.str.strip()
        
        # Carrega a aba USUÁRIOS
        try:
            df_usuarios = pd.read_csv(URL_USUARIOS, dtype=str)
            df_usuarios.columns = df_usuarios.columns.str.strip()
        except Exception:
            df_usuarios = pd.DataFrame()

        cnpj_busca = limpar_cnpj(dados_pdf["CNPJ"])
        
        # 1. LOCALIZA A LOJA PELO CNPJ
        col_cnpj_lojas = 'CNPJ' if 'CNPJ' in df_lojas.columns else df_lojas.columns[3]
        df_lojas['CNPJ_Limpo'] = df_lojas[col_cnpj_lojas].apply(limpar_cnpj)
        
        linha_loja = df_lojas[df_lojas['CNPJ_Limpo'] == cnpj_busca]
        
        if linha_loja.empty: 
            return {"status": "Não Encontrado", "mensagem": "CNPJ não localizado na aba LOJAS."}
        
        loja = linha_loja.iloc[0]
        checklist = {}
        divergencias = 0

        rede_da_loja = normalizar_texto(loja.get('Rede', '')) or normalizar_texto(loja.get('Bandeira', ''))

        # 2. BUSCA PROPRIETÁRIOS E REPRESENTANTES DA REDE
        proprietarios_encontrados = []
        representantes_rede_planilha = []

        if not df_usuarios.empty:
            col_cnpj_user = 'CNPJ - Loja' if 'CNPJ - Loja' in df_usuarios.columns else 'CNPJ'
            col_nome_user = 'Nome Completo' if 'Nome Completo' in df_usuarios.columns else 'Nome'
            
            if col_cnpj_user in df_usuarios.columns:
                df_usuarios['CNPJ_Limpo'] = df_usuarios[col_cnpj_user].apply(limpar_cnpj)
                usuarios_loja = df_usuarios[df_usuarios['CNPJ_Limpo'] == cnpj_busca]
                
                if col_nome_user in usuarios_loja.columns:
                    proprietarios_raw = usuarios_loja[col_nome_user].dropna().unique().tolist()
                    proprietarios_encontrados = [normalizar_texto(n) for n in proprietarios_raw]

            col_perfil = 'Perfil' if 'Perfil' in df_usuarios.columns else ''
            col_cargo = 'Cargo' if 'Cargo' in df_usuarios.columns else ''
            col_rede_user = 'Rede' if 'Rede' in df_usuarios.columns else 'Bandeira - Loja'

            if col_perfil and col_cargo and col_nome_user:
                cond_rede_perfil = df_usuarios[col_perfil].astype(str).str.strip().str.upper() == 'REDE'
                cond_cargo = df_usuarios[col_cargo].astype(str).str.strip().str.upper().isin(['PRESIDENTE', 'DIRETOR'])
                
                if rede_da_loja and col_rede_user in df_usuarios.columns:
                    cond_pertence_rede = df_usuarios[col_rede_user].astype(str).apply(normalizar_texto) == rede_da_loja
                    filtro_final = cond_rede_perfil & cond_cargo & cond_pertence_rede
                else:
                    filtro_final = cond_rede_perfil & cond_cargo

                rep_raw = df_usuarios[filtro_final][col_nome_user].dropna().unique().tolist()
                representantes_rede_planilha = [normalizar_texto(n) for n in rep_raw]

        # 3. MONTAGEM DO CHECKLIST
        # A) PROPRIETÁRIO
        nome_pdf = normalizar_texto(dados_pdf.get("Nome", ""))
        str_proprietarios_planilha = ", ".join(dict.fromkeys(proprietarios_encontrados)) if proprietarios_encontrados else "Nenhum cadastrado"
        
        ok_nome = False
        if nome_pdf and proprietarios_encontrados:
            ok_nome = any(nome_pdf in p or p in nome_pdf for p in proprietarios_encontrados)
            
        checklist["Proprietário"] = {
            "ok": ok_nome, 
            "pdf": dados_pdf.get("Nome"), 
            "planilha": str_proprietarios_planilha
        }
        if not ok_nome: divergencias += 1

        # B) RAZÃO SOCIAL
        col_razao = 'Razão Social' if 'Razão Social' in loja.index else df_lojas.columns[4]
        razao_pdf = normalizar_texto(dados_pdf.get("Razão Social", ""))
        razao_planilha = normalizar_texto(loja.get(col_razao, ''))
        
        ok_razao = False
        if razao_pdf and razao_planilha:
            ok_razao = (razao_pdf in razao_planilha) or (razao_planilha in razao_pdf) or (re.sub(r'\W+', '', razao_pdf) == re.sub(r'\W+', '', razao_planilha))
        
        checklist["Razão Social"] = {
            "ok": ok_razao, 
            "pdf": dados_pdf.get("Razão Social"), 
            "planilha": loja.get(col_razao)
        }
        if not ok_razao: divergencias += 1

        # C) RESPONSÁVEL PELA REDE
        resp_pdf = normalizar_texto(dados_pdf.get("Responsável Rede", ""))
        reps_unicos = list(dict.fromkeys(representantes_rede_planilha))
        str_resp_rede_planilha = ", ".join(reps_unicos) if reps_unicos else f"Nenhum Presidente/Diretor para a rede '{rede_da_loja}'"
        
        ok_resp = False
        if resp_pdf and reps_unicos:
            ok_resp = any(resp_pdf in r or r in resp_pdf for r in reps_unicos)

        checklist["Responsável pela Rede"] = {
            "ok": ok_resp, 
            "pdf": dados_pdf.get("Responsável Rede"), 
            "planilha": str_resp_rede_planilha
        }
        if not ok_resp: divergencias += 1

        status_final = "Aprovado" if divergencias == 0 else "Divergente"
        return {"status": status_final, "checklist": checklist}

    except Exception as e:
        return {"erro": f"Erro ao processar as abas da planilha: {str(e)}"}