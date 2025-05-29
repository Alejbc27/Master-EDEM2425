from langchain_google_genai import ChatGoogleGenerativeAI
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def setup_llm():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0.3)
    config = {"configurable": {"thread_id": "1"}}
    return llm, config

def setup_infermedica_headers():

    app_id = os.getenv("INFERMEDICA_APP_ID")
    app_key = os.getenv("INFERMEDICA_APP_KEY")
    
    HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Dev-Mode": "true",
        'App-Id': "X",
        'App-Key': "X"
    }
    return HEADERS