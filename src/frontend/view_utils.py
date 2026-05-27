import streamlit as st


def resposta_agente_para_texto(resposta: object) -> str:
    if isinstance(resposta, dict):
        output = resposta.get("output", resposta)
    else:
        output = resposta

    if isinstance(output, str):
        return output
    if isinstance(output, list):
        partes = []
        for item in output:
            if isinstance(item, dict):
                partes.append(str(item.get("text") or item.get("content") or item))
            else:
                partes.append(str(item))
        return "\n".join(partes)
    return str(output)


def _extrair_json_resposta(texto: object) -> str:
    texto = resposta_agente_para_texto(texto)
    cleaned = texto.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    inicio = cleaned.find("{")
    fim = cleaned.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        return cleaned[inicio : fim + 1]
    return cleaned


def render_confidence_gauge(breakdown: dict, key: str = "") -> None:
    score = float(breakdown.get("confianca_total") or 0)
    nivel = str(breakdown.get("confianca_nivel") or "Insuficiente")
    color_map = {
        "Alta": ("#00875A", "#E3FCEF"),
        "Media": ("#FF991F", "#FFF4E5"),
        "Média": ("#FF991F", "#FFF4E5"),
        "Baixa": ("#DE350B", "#FFEBE6"),
        "Insuficiente": ("#6B778C", "#F4F5F7"),
    }
    cor_texto, cor_fundo = color_map.get(nivel, ("#6B778C", "#F4F5F7"))

    st.markdown(
        f"""
        <div style="background:{cor_fundo}; border-left: 4px solid {cor_texto};
                    padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
            <span style="color:{cor_texto}; font-weight:700; font-size:15px;">
                Confianca {nivel}: {score:.0f}/100
            </span><br>
            <span style="font-size:12px; color:#44546F;">
                {breakdown.get('confianca_resumo', '')}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        valor = float(breakdown.get("confianca_dados") or 0)
        st.metric("Dados", f"{valor:.0f}/40")
        st.progress(max(0.0, min(valor / 40, 1.0)))
        ausentes = str(breakdown.get("dados_ausentes_criticos") or "").strip()
        if ausentes:
            st.caption(f"Ausentes: {ausentes}")
    with c2:
        valor = float(breakdown.get("confianca_sinais") or 0)
        st.metric("Sinais", f"{valor:.0f}/35")
        st.progress(max(0.0, min(valor / 35, 1.0)))
    with c3:
        valor = float(breakdown.get("confianca_contexto") or 0)
        st.metric("Contexto", f"{valor:.0f}/25")
        st.progress(max(0.0, min(valor / 25, 1.0)))


