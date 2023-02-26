from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import VectorDBQA
from langchain.document_loaders import TextLoader
from langchain import PromptTemplate
from fastapi import FastAPI
from langchain.llms import OpenAI



app = FastAPI()

DATA = '../data/cointelegraph_20230221_test.json'
LLM = OpenAI(model_name="text-davinci-003", temperature=0.5, best_of=10, n=3, max_tokens=200)
VECTORDB = None
RAG_TEMPLATE = """
I want you to act as a crypto analyst working at coinbase writing about crypto currency.

Base yor answer on the following articles:
{article_1}
{article_2}
{article_3}
{article_4}

Answer the following question:
{question}
"""


@app.on_event("startup")
async def startup_event():
    """Should be connecting to search engine here, but for demo we are brute
    forcing shit.
    """
    loader = TextLoader(DATA)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()
    global VECTORDB
    VECTORDB = Chroma.from_documents(texts, embeddings)


def retrieval_augumented_generation(*, query=query):
    """Do a retrieval augumented generation against the preloaded vectorDB
    and generate languages using the preset prompt template.

    Args:
        query (_type_, optional): _description_. Defaults to query.

    Returns:
        _type_: _description_
    """
    hits = VECTORDB.similarity_search(query=query)

    prompt = PromptTemplate(
        input_variables=["question", "article_1", "article_2", "article_3", "article_4"],
        template=RAG_TEMPLATE,
    )
    prompt_data = {
    "question": query,
    "article_1": hits_page_content[0],
    "article_2": hits_page_content[1],
    "article_3": hits_page_content[2],
    "article_4": hits_page_content[3],
    }
    prompt.format(**prompt_data)
    return LLM(prompt.format(**prompt_data))

def generate(*, query=query):
    return LLM(query)

@app.post("/generate/{count_id}")
async def generate(count_id: str, query: str):
    if count_id == "1":
        return retrieval_augumented_generation(query=query)
    else:
        return generate(query=query)
