from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_nomic import NomicEmbeddings
from langchain_core.documents import Document
import src.config as config
import os
from .logger import AppLogger

os.environ["USER_AGENT"] = "my-rag-app/1.0"

logger = AppLogger()

embeddings = NomicEmbeddings(model=config.EMBEDDING_MODEL)

def get_or_create_chroma(persist_dir, embeddings, documents=None):
    """Load Chroma if exists, otherwise crate it from documents."""
    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        logger.info("Loading existing Chroma store...")
        return Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    else:
        logger.info("Creating new Chroma store...")
        vectorstore = Chroma.from_documents(
            documents=documents, embedding=embeddings, persist_directory=persist_dir
        )
        return vectorstore

def main():
    loader = WebBaseLoader("https://cartagenawomen.com/")
    loader.requests_kwargs = {'verify': False}
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    split_docs = splitter.split_documents(docs)

    vectorstore = get_or_create_chroma(config.PERSIST_DIRECTORY, embeddings, split_docs)
    logger.info("Vectorstore ready.")
    
if __name__ == "__main__":
    main()