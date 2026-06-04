import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

def handle_respons(user_questions):
    if st.session_state.conversation is None:
        st.error("Conversation tidak tersedia. Pastikan PDF sudah diproses terlebih dahulu")
        return

    # Tampilkan semua riwayat chat sebelumnya
    for message in st.session_state.chat_history:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.write(message.content)

    with st.chat_message("user"):
        st.write(user_questions)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # New format for calling version v0.3
            response = st.session_state.conversation.invoke({
                "input": user_questions,
                "chat_history": st.session_state.chat_history
            })

        # Get the answer and save to history (only once)
        assistant_reply = response['answer']

        st.session_state.chat_history.append(HumanMessage(content=user_questions))
        st.session_state.chat_history.append(AIMessage(content=assistant_reply))

        st.write(assistant_reply)
        
"""
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.conversation({'question': user_questions})
            st.session_state.chat_history = response['chat_history']
        
            for i, message in st.session_state.chat_history:
                if i % 2 == 0:
                    st.chat_message("user").write(message.content)
                else:
                    st.chat_message("assistant").write(message.content)
"""