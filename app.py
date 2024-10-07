import multiprocessing
import os
import uuid
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

import gradio as gr
from langchain_core.messages import HumanMessage

from react_agent import graph


# Chemins et port configurables via les variables d'environnement
DIRECTORY = os.getenv('DIRECTORY', "./tmp")
PORT = int(os.getenv('PORT', 8000))


# Configuration initiale
config = {
    "configurable": {"thread_id": str(uuid.uuid4())}
}

def call_graph(message, history):
    """Appelle la fonction `graph.invoke` avec le message utilisateur et renvoie la réponse."""
    try:
        response = graph.invoke({
            "messages": [HumanMessage(content=message)]
        }, config=config)
        return response['messages'][-1].content
    except Exception as e:
        print(f"Erreur lors de l'appel à graph.invoke : {e}")
        return "Une erreur est survenue lors du traitement de votre message."


# Créer l'interface utilisateur Gradio
demo = gr.ChatInterface(fn=call_graph, title="Advisor", multimodal=False, undo_btn=None, retry_btn=None)


def run_ui():
    """Lancer l'interface utilisateur Gradio."""
    try:
        demo.launch()
    except Exception as e:
        print(f"Erreur lors du lancement de l'interface utilisateur : {e}")


def run_static_server():
    """Lancer un serveur HTTP statique pour servir des fichiers depuis un répertoire."""

    class StaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DIRECTORY, **kwargs)

    try:
        with TCPServer(("", PORT), StaticHandler) as httpd:
            print(f"Serving at port {PORT} from directory {DIRECTORY}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur HTTP : {e}")


if __name__ == "__main__":
    # Créer et démarrer les processus pour le serveur et l'interface utilisateur
    p1 = multiprocessing.Process(target=run_ui)
    p2 = multiprocessing.Process(target=run_static_server)

    try:
        p1.start()
        p2.start()

        p1.join()
        p2.join()
    except KeyboardInterrupt:
        print("Arrêt demandé par l'utilisateur. Fermeture des processus...")
    except Exception as e:
        print(f"Erreur lors de l'exécution des processus : {e}")
    finally:
        # Terminer les processus proprement
        p1.terminate()
        p2.terminate()
        p1.join()
        p2.join()
