import logging
import pandas as pd
from langchain.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from PyPDF2 import PdfReader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain

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

def get_vectorstore(text_splitter):
    model_name = 'hkunlp/instructor-xl'
    persist_directory = f"db_{model_name.replace('/', '_')}"

    logging.info(f"Load pretrained SentenceTransformers {model_name}")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    logging.info(f"Successfully loaded {model_name}")

    logging.info(f"Loading FAISS....")
    #vectorstores = Chroma.from_texts(texts=text_splitter, persist_directory=persist_directory, embedding=embeddings)
    vectorstores = FAISS.from_texts(texts=text_splitter, embedding=embeddings)
    logging.info(f"Successfully loaded FAISS")

    if vectorstores:
        print("Success Process PDF")
    else:
        print("Failed Process PDF")

    return vectorstores

def get_conversation(vectorstore, model_llm, groq_api_key):
    retrievar = vectorstore.as_retriever(search_type='mmr', kwargs={'k':3})

    if not groq_api_key and groq_api_key.strip() == "":
        raise ValueError("Groq API key kosong atau tidak valid")
    
    llm = ChatGroq(model=model_llm, groq_api_key=groq_api_key)
    logging.info(f"Using model: {model_llm}")

    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    conversation = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retrievar, memory=memory)

    return conversation

# Processing file excel & csv

def read_data(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)
