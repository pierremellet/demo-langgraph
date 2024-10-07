import json
import operator
import sqlite3
import uuid
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import Field, BaseModel

from llm_provider import llm


# Classes de schémas et typages
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


class ExecSQLSchema(BaseModel):
    query: str = Field(description="An SQL Query")


class ChartHistSerie(BaseModel):
    title: str = Field(description="Serie name")
    labels: list[str] = Field(description="List of labels for X axis")
    values: list[float] = Field(description="List of values for Y axis")


class ChartHistSchema(BaseModel):
    title: str = Field(description="Chart title")
    type: str = Field(description="Dataviz type (ex: piechart, barchart, linechart, etc.)")
    series: list[ChartHistSerie] = Field(description="Chart series list")


@tool(args_schema=ChartHistSchema)
def chart_hist(type: str, title: str, series: list[ChartHistSerie]) -> str:
    """Generate a markdown content with a data visualization image."""
    file = f"{uuid.uuid4()}.png"

    # Utiliser un prompt pour générer le code Python via OpenAI
    prompt = PromptTemplate.from_template("""
        Tu es un expert du code Python et de la librairie matplotlib.
        Génère un code Python pour créer une visualisation de type {type}, portant le nom {title}.
        La visualisation doit présenter les séries de données suivantes :
        {series}
        
        Chaque série est caractérisée par un titre (title), une liste des labels et les données (values) correspondantes.
        
        Utilise le chemin suivant pour enregistrer l'image : {path}
    """)


    class Output(BaseModel):
        python_source_code: str = Field(description="Executable Python source code")
        comments: str = Field(description="A comment that describes the source code")

    # Appel au modèle pour générer le code Python
    code_python = (prompt | llm.with_structured_output(Output)).invoke({
        "type": type,
        "title": title,
        "series": [s.model_dump() for s in series],
        "path": f"tmp/{file}"
    })

    print(code_python.python_source_code)

    # Éviter d'utiliser `exec` directement pour des raisons de sécurité.
    exec(code_python.python_source_code)

    url = f"http://localhost:8000/{file}"

    return f"""
    ```markdown
    ![Histogram]({url})
    """


@tool(args_schema=ExecSQLSchema)
def exec_sql(query: str) -> str:
    """Execute a SQL query against the customer database."""
    try:
        print(query)
        with sqlite3.connect("tx.db") as con:
            cur = con.cursor()
            res = cur.execute(query)
            return json.dumps(res.fetchall())
    except sqlite3.Error as e:
        return json.dumps({"error": str(e)})


# Template de prompt pour l'agent
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content="""
    Tu es un agent spécialisé dans la recherche d'informations sur des transactions de clients bancaires.
    
    Les transactions bancaires sont enregistrées dans une base de données créée avec les instructions suivantes :
    
        CREATE TABLE Client (
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            account_number VARCHAR(34) PRIMARY KEY NOT NULL -- IBAN format with max length of 34 characters
        );
        
        CREATE TABLE AccountTransaction (
            account_number VARCHAR(34) NOT NULL,
            transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
            amount DECIMAL(10, 2) NOT NULL  -- Positive value means credit in Euros and negative value means debit in euro,
            category VARCHAR(50) NOT NULL CHECK (category IN ('TAXES', 'ENERGY', 'RESTAURANT', 'CLOTHES', 'SALARY', 'HOBBY')),
            label VARCHAR(255) NOT NULL,
            FOREIGN KEY (account_number) REFERENCES Client(account_number)
        );
    
    Si amount est positif, c'est un crédit.
    Si amount est négatif, c'est un débit.
    
    Réponds aux questions concernant les transactions en formatant les réponses sous forme de tableau Markdown.
    """),
    MessagesPlaceholder(variable_name="messages")
])


tools = [exec_sql, chart_hist]
llm_with_tools = llm.bind_tools(tools)


# Fonction pour exécuter l'agent dans un nœud du graphe
def chatbot_node(state: AgentState):
    """Exécuter l'agent sur l'état donné."""
    runnable = (prompt | llm_with_tools)
    res = runnable.invoke(state['messages'])
    return {"messages": [res]}


# Construction du graphe d'état
graph_builder = StateGraph(AgentState)
graph_builder.add_node("tools", ToolNode(name="tools", tools=tools))
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.set_entry_point("chatbot")
graph_builder.set_finish_point("chatbot")
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)

# Sauvegarde et compilation du graphe
checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer, debug=False)
