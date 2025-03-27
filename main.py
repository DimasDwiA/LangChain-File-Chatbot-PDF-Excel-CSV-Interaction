import os
import logging
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_experimental.agents import create_pandas_dataframe_agent
from googletrans import LANGUAGES as googletrans_languages
from answer_questions import handle_respons
from processing_file import get_text_pdf, get_text_chunks, get_vectorstore, get_conversation, read_data

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO, handlers=[logging.FileHandler("app.log"),
                                                                                    logging.StreamHandler()])
def reset_chat_state():
    key_history = ['conversation', 'chat_history','pdf_processed', 'vectorstore', 'chat_history_excel_csv', 'df']
    for key in key_history:
        if key in st.session_state:
            del st.session_state[key]

def main():

    load_dotenv()

    api_key = os.getenv("LANGCHAIN_API_KEY") 
    if api_key:
        groq_api_key = os.getenv("GROQ_API_KEY")
        os.environ['LANGCHAIN_API_KEY'] = api_key
        os.environ['LANGCHAIN_PROJECT'] = os.getenv("LANGCHAIN_PROJECT")
        os.environ['LANGCHAIN_TRACING'] = "true"
        os.environ['HUGGINGFACEHUB_API_TOKEN'] = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    else:
        print("Tidak ada API Key")

    option = ["Chatbot for Ask Your PDF & Translation PDF", "Chatbot for Analysis Excel/CSV"]

    with st.sidebar:
        st.title("🦜️🔗 Chatbot to Ask Your PDF, Excel/CSV, & Translation Document Using LLM Model")
        select_option = st.selectbox("Choose Your Needs to Ask Deeper Questions", option,
                                     index=option.index(st.session_state.get("last_selected_chatbot", option[0])))
        
        if 'last_selected_chatbot' not in st.session_state:
            st.session_state.last_selected_chatbot = select_option

        if select_option != st.session_state.get("last_selected_chatbot"):
            st.warning("""
            ⚠️ Warning: Switching between chatbot modes will reset your current chat and uploaded files. 
            - Any processed PDF or uploaded Excel/CSV will be cleared.
            - Your chat history will be lost.

            """)
            
            reset_chat_state()
            st.session_state.last_selected_chatbot = select_option
        
    if select_option == "Chatbot for Ask Your PDF & Translation PDF":
        st.title("Find Out More Deeply About Your PDF Using A Chatbot")
        st.write("This chatbot can help you find out more about your PDF")

        option_model = ["llama-3.3-70b-versatile", "qwen-2.5-32b", "gemma2-9b-it", "mistral-saba-24b"]
        model_llm = st.selectbox("Choose Your Model to Answer Your Questions", option_model)

        if 'conversation' not in st.session_state:
            st.session_state.conversation = None
        if 'vectorstore' not in st.session_state:
            st.session_state.vectorstore = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'pdf_processed' not in st.session_state:
            st.session_state.pdf_processed = False

        pdfs = st.file_uploader("Upload Your PDF & Click on 'Process'", type="PDF", accept_multiple_files=True)
        if pdfs and not st.session_state.pdf_processed:
            with st.spinner("Processing Your PDF"):
                # Get text from pdf
                raw_text = get_text_pdf(pdfs)

                # Text splitter 
                text_splitter = get_text_chunks(raw_text)

                # Create vector store
                st.session_state.vectorstore = get_vectorstore(text_splitter)
            
                if st.session_state.vectorstore:
                    st.session_state.pdf_processed = True

                    # Create conversation
                    st.session_state.conversation = get_conversation(st.session_state.vectorstore, 
                                                                 model_llm, groq_api_key)
                else:
                    st.write("❌ Failed to process your PDF")

        elif not pdfs:
            st.warning("Please process a PDF first before asking questions.")

        if st.session_state.pdf_processed:
            st.success("✅ Success processing your PDF! You can now ask questions")

            toogle = st.checkbox("Include translation of the document")

            if toogle:
                st.info("🔧 This feature is under development.⏳We are working hard to get it done! So please be super patient! 😊")
                #with st.form("Language Selection"):
                #    st.write("Select Language for the documennt")
                #    st.selectbox("Select Language:", list(googletrans_languages.values()))
                #    st.form_submit_button("Apply")

        user_question = st.chat_input("Ask questions about the PDF you've uploaded", key="user_input")
        if user_question:
            if st.session_state.pdf_processed and st.session_state.conversation:
                handle_respons(user_question)

    else:
        st.title("Find Out More Deeply About Your Excel/CSV Using A Chatbot to Analyze Your Data")
        st.write("This chatbot can help you analyze your data from excel/csv you've uploaded")

        option_model = ["llama-3.3-70b-versatile", "qwen-2.5-32b", "gemma2-9b-it", "mistral-saba-24b"]
        model_llm = st.selectbox("Choose Your Model to Answer Your Questions", option_model)

        if 'chat_history_excel_csv' not in st.session_state:
            st.session_state.chat_history_excel_csv = []
        if 'df' not in st.session_state:
            st.session_state.df = None

        excel_csv = st.file_uploader("Upload Your file (Excel/CSV) & Click on 'Process'", type=['xls', 'xlsx', 'csv'])
        if excel_csv:
            with st.spinner("Processing Your file"):
                st.session_state.df = read_data(excel_csv)
                st.write("Preview DataFrame: ")
                st.dataframe(st.session_state.df.head())

        elif not excel_csv:
            st.warning("Please upload your file (Excel/CSV) first before asking questions.")

        for messages in st.session_state.chat_history_excel_csv:
            with st.chat_message(messages['role']):
                st.write(messages['content'])

        user_prompt = st.chat_input("Ask questions about the Excel/CSV you've uploaded for Analysis", key="user_input")

        if user_prompt:
            st.chat_message("user").markdown(user_prompt)
            st.session_state.chat_history_excel_csv.append({'role':'user', 'content':user_prompt})

            llm = ChatGroq(model=model_llm, groq_api_key=groq_api_key)

            pandas_agent = create_pandas_dataframe_agent(
                llm, st.session_state.df, verbose=True, agent_type= 'openai-tools', allow_dangerous_code=True
            )

            messages = [{"role": "system", "content": "You're a helpful assistant"},
                       *st.session_state.chat_history_excel_csv]
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking....."):
                    try:
                        response = pandas_agent.run(user_prompt)
                        assistant_response = response
                        st.markdown(assistant_response)
                    except Exception as e:
                        st.error(f"An error occured: {e}")
                        assistant_response = "I'm sorry, I couldn't process your request. Please try rephrasing or check your data."

            st.session_state.chat_history_excel_csv.append({'role':'assistent', 'content': assistant_response})

if __name__=="__main__":
    main()
