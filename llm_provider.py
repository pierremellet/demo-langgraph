from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
#from langchain_google_vertexai import ChatVertexAI
#llm = ChatVertexAI(
#    model="gemini-1.5-flash-001",
#    temperature=0,
#    max_tokens=None,
#    max_retries=6,
#    stop=None
#)