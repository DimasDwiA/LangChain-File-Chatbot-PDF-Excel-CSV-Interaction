import logging
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from PyPDF2 import PdfReader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Processing file PDF

def get_text_pdf(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator='\n',
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    model_name = 'hkunlp/instructor-xl'

    logging.info(f"Load pretrained SentenceTransformers {model_name}")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    logging.info(f"Successfully loaded {model_name}")

    logging.info("Loading FAISS....")
    vectorstores = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    logging.info("Successfully loaded FAISS")

    if vectorstores:
        print("Success Process PDF")
    else:
        print("Failed Process PDF")

    return vectorstores

def get_conversation(vectorstore, model_llm, groq_api_key):
    retriever = vectorstore.as_retriever(search_type='mmr', search_kwargs={'k': 3})

    if not groq_api_key or groq_api_key.strip() == "":
        raise ValueError("Groq API key kosong atau tidak valid")

    llm = ChatGroq(model=model_llm, groq_api_key=groq_api_key)
    logging.info(f"Using model: {model_llm}")

    # --- Prompt: reformulate question given chat history ---
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # --- Prompt: answer with retrieved context ---
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know."
        "\n\n"
        "{context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    # Chain that reformulates the question if there is chat history
    contextualized_q_chain = contextualize_q_prompt | llm | StrOutputParser()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def retrieve_context(input_dict):
        """Reformulate question when history exists, then retrieve relevant docs."""
        if input_dict.get("chat_history"):
            standalone_question = contextualized_q_chain.invoke(input_dict)
        else:
            standalone_question = input_dict["input"]
        docs = retriever.invoke(standalone_question)
        return format_docs(docs)

    # Full LCEL chain — output wrapped as {'answer': ...} to match existing code
    conversation_chain = (
        RunnablePassthrough.assign(context=retrieve_context)
        | qa_prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(lambda answer: {"answer": answer})
    )

    return conversation_chain

# Processing file excel & csv
def read_data(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)