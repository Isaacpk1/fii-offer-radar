import streamlit as st
from langchain_classic.memory import ConversationBufferMemory

from ai_core.agent import inicializar_agente_analista


def carregar_agente():
    if "agent_memory" not in st.session_state:
        st.session_state.agent_memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
        )
    if "agente" not in st.session_state:
        st.session_state.agente = inicializar_agente_analista(memory=st.session_state.agent_memory)
    return st.session_state.agente
