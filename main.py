import os
import csv
import json
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext, Settings, Document
from llama_index.core.agent import ReActAgent
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from qdrant_client import QdrantClient
import pdfplumber
import tiktoken
import gradio as gr
from tools import Tools

# === Load .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("No se encontró la variable de entorno OPENAI_API_KEY")

# === READERS ===

class CSVReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def load_data(self):
        documents = []
        with open(self.file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = (
                    f"El id del pedido es {row['order_id']}, Cliente ID: {row['customer_id']}, "
                    f"Producto: {row['product']}, Categoría: {row['category']}, "
                    f"Cantidad: {row['quantity']}, Precio: {row['price']}, "
                    f"Fecha: {row['order_date']}, Estado: {row['estado']}"
                )
                metadata = {
                    "order_id": row["order_id"],
                    "customer_id": row["customer_id"],
                    "product": row["product"],
                    "category": row["category"],
                    "price": row["price"],
                    "quantity": row["quantity"],
                    "order_date": row["order_date"],
                    "payment_method": row["payment_method"],
                    "estado": row["estado"]
                }
                documents.append(Document(text=text, metadata=metadata))
        return documents

class JSONReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def load_data(self):
        documents = []
        with open(self.file_path, encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                text = f"Pregunta: {item['question']} -> Respuesta: {item['answer']}"
                documents.append(Document(text=text))
        return documents

# === Load data ===
# Cargar CSV de pedidos para RAG
csv_docs = CSVReader("./data/pedidos/pedidos.csv").load_data()

# Cargar CSV de pedidos para Tools (DataFrame)
pedidos_df = pd.read_csv("./data/pedidos/pedidos.csv")

# Cargar FAQ
json_docs = JSONReader("./data/faq/faq.json").load_data()

# === Initialize Qdrant ===
qdrant_client = QdrantClient(url="http://localhost:6333")
agents_collections = {
    "pedidos": QdrantVectorStore(collection_name="pedidos", client=qdrant_client),
    "faq": QdrantVectorStore(collection_name="faq", client=qdrant_client),
}

storage_contexts = {
    agent: StorageContext.from_defaults(vector_store=vector_store)
    for agent, vector_store in agents_collections.items()
}

# === Set up OpenAI LLM and embeddings ===
llm = OpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0)
Settings.llm = llm
embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.embed_model = embed_model

# === Load system prompts ===
def load_system_prompt(agent_name: str) -> str:
    prompt_file = f"./prompts/{agent_name}.txt"
    if not os.path.exists(prompt_file):
        return ""
    with open(prompt_file, encoding="utf-8") as f:
        return f.read()


system_prompts = {
    "devoluciones": load_system_prompt("devoluciones"),
    "pedidos": load_system_prompt("pedidos"),
    "faq": load_system_prompt("faq"),
}

# === Create indices (solo para pedidos y FAQ) ===
indexes = {}
for agent_name, docs in [("pedidos", csv_docs), ("faq", json_docs)]:
    indexes[agent_name] = VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_contexts[agent_name],
        embed_model=embed_model
    )

# === Create Tools for Devoluciones Agent ===
tools_manager = Tools(pedidos_df)
devoluciones_tools = tools_manager.get_tools()

# === Create Devoluciones Agent with Tools ===
devoluciones_agent = ReActAgent.from_tools(
    tools=devoluciones_tools,
    llm=llm,
    verbose=True,
    max_iterations=10,
    system_prompt=system_prompts["devoluciones"]
)

# GRADIO CHAT
def chat_with_agent(agent_choice, user_input, chat_history):
    if not user_input:
        return chat_history

    if agent_choice == "devoluciones":
        try:
            response = devoluciones_agent.chat(user_input)
        except Exception as e:
            response = f"❌ Error en el agente de devoluciones: {str(e)}"

    elif agent_choice == "pedidos":
        try:
            user_input_upper = user_input.upper()
            if "O" in user_input_upper and any(char.isdigit() for char in user_input):
                retriever = indexes["pedidos"].as_retriever(similarity_top_k=3)
                results = retriever.retrieve(user_input)
                if results:
                    pedido_info = results[0].metadata
                    response = "📦 Información del pedido:\n"
                    response += "\n".join([f"• {k}: {v}" for k, v in pedido_info.items()])
                else:
                    response = "❌ No se encontró información sobre el pedido solicitado."
            else:
                query_engine = indexes["pedidos"].as_query_engine(
                    retriever_mode="embedding",
                    response_mode="compact",
                    system_prompt=system_prompts["pedidos"]
                )
                response = query_engine.query(user_input)
        except Exception as e:
            response = f"❌ Error: {str(e)}"

    elif agent_choice == "faq":
        try:
            query_engine = indexes["faq"].as_query_engine(
                retriever_mode="embedding",
                response_mode="compact",
                system_prompt=system_prompts["faq"]
            )
            response = query_engine.query(user_input)
        except Exception as e:
            response = f"❌ Error: {str(e)}"
    else:
        response = "❌ Selecciona un agente válido."
    
    if not isinstance(response, str):
        response = str(response)
    
    chat_history.append((user_input, response))
    return chat_history



# === Interfaz Gradio ===
with gr.Blocks() as demo:
    gr.Markdown('''## 🌱 E-COMMERCE ECOLÓGICO - Sistema de Atención al Cliente
                ### AGENTE DE PEDIDOS: SE PUEDE HACER PREGUNTAS SOBRE IDS ESPECIFICOS DE PEDIDOS.
                ### AFENTE DE DEVOLUCIONES: SE REQUIERE EL ID DEL USUARIO PARA INICIAR EL PROCESO DE DEVOLUCIÓN.
                ### AGENTE DE FAQ: PREGUNTAS GENERALES SOBRE LA TIENDA.''')
    
    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=["devoluciones", "pedidos", "faq"],
            label="Selecciona un agente",
            value="devoluciones"
        )
    
    chatbox = gr.Chatbot(label="Chat", type="tuples")
    user_input = gr.Textbox(label="Tu mensaje", placeholder="Escribe aquí...")
    submit_btn = gr.Button("Enviar")



    def wrapped_chat(agent_choice, user_input, chat_history):
        
        chat_history = chat_with_agent(agent_choice, user_input, chat_history)
        
        return chat_history

    submit_btn.click(
        wrapped_chat,
        inputs=[agent_dropdown, user_input, chatbox],
        outputs=chatbox
    )

demo.launch()




'''# === Interfaz Gradio ===
with gr.Blocks() as demo:
    gr.Markdown("## 🌱 E-COMMERCE ECOLÓGICO - Sistema de Atención al Cliente")
    
    with gr.Row():
        agent_dropdown = gr.Dropdown(
            choices=["devoluciones", "pedidos", "faq"],
            label="Selecciona un agente",
            value="devoluciones"
        )
    
    chatbox = gr.Chatbot(label="Chat")
    user_input = gr.Textbox(label="Tu mensaje", placeholder="Escribe aquí...")
    submit_btn = gr.Button("Enviar")
    
    submit_btn.click(
        chat_with_agent,
        inputs=[agent_dropdown, user_input, chatbox],
        outputs=chatbox
    )

demo.launch()'''



'''# === Agent selection function ===
def choose_agent():
    print("\n" + "="*60)
    print("🌱 E-COMMERCE ECOLÓGICO - SISTEMA DE ATENCIÓN AL CLIENTE")
    print("="*60)
    print("\nSelecciona un agente:")
    print("1 - 🔄 Devoluciones (con Tools)")
    print("2 - 📦 Pedidos (RAG)")
    print("3 - ❓ Preguntas Frecuentes (RAG)")
    print("0 - 🚪 Salir")
    print("-"*60)
    choice = input("Ingresa tu opción: ").strip()
    mapping = {"1": "devoluciones", "2": "pedidos", "3": "faq", "0": "exit"}
    return mapping.get(choice, None)

# === Main chat loop ===
print("\n¡Bienvenido al sistema de atención al cliente!")
print("Escribe 'back' para volver al menú principal")
print("Escribe 'exit' para salir del programa\n")

count = 0
while True:
    agent_choice = choose_agent()
    
    if agent_choice == "exit":
        print("\n👋 ¡Gracias por usar nuestro sistema! Hasta pronto.")
        break
    elif agent_choice is None:
        print("❌ Opción inválida. Intenta de nuevo.")
        continue

    print(f"\n{'='*60}")
    print(f"🤖 Agente activo: {agent_choice.upper()}")
    print(f"{'='*60}\n")

    # Instrucciones específicas por agente
    if agent_choice == 'pedidos' and count == 0:
        print("💡 TIPS PARA CONSULTAR PEDIDOS:")
        print("   • Proporciona el order_id (ej: O0001) o customer_id (ej: C001)")
        print("   • Incluye detalles como nombre, producto o fecha si es posible")
        print("   • El sistema usa embeddings para buscar coincidencias\n")
        count += 1
    
    if agent_choice == 'devoluciones':
        print("💡 TIPS PARA DEVOLUCIONES:")
        print("   • Proporciona tu order_id (ej: O0001)")
        print("   • Si no lo conoces, proporciona tu customer_id (ej: C001)")
        print("   • El agente evaluará automáticamente la elegibilidad\n")

    # Loop de conversación por agente
    while True:
        user_input = input("Tú: ").strip()
        
        if user_input.lower() == "back":
            print("\n↩️  Regresando al menú principal...\n")
            break
        elif user_input.lower() == "exit":
            print("\n👋 ¡Hasta pronto!")
            exit()
        elif not user_input:
            continue

        print()  # Línea en blanco para mejor lectura
        
        # AGENTE DE DEVOLUCIONES (con Tools)
        if agent_choice == "devoluciones":
            try:
                response = devoluciones_agent.chat(user_input)
                print(f"EcoAsistente: {response}\n")
            except Exception as e:
                print(f"❌ Error en el agente de devoluciones: {str(e)}\n")
                print("Por favor, intenta reformular tu pregunta.\n")

        # AGENTE DE PEDIDOS (RAG con filtrado)
        elif agent_choice == "pedidos":
            try:
                # Intentar extraer order_id o customer_id del input
                user_input_upper = user_input.upper()
                
                # Buscar por order_id exacto
                if "O" in user_input_upper and any(char.isdigit() for char in user_input):
                    retriever = indexes["pedidos"].as_retriever(similarity_top_k=3)
                    results = retriever.retrieve(user_input)
                    
                    if results:
                        # Mostrar información del pedido encontrado
                        print("📦 Información del pedido:\n")
                        pedido_info = results[0].metadata
                        for k, v in pedido_info.items():
                            print(f"   • {k}: {v}")
                        print()
                    else:
                        print(f"❌ No se encontró información sobre el pedido solicitado.\n")
                else:
                    # Búsqueda general
                    query_engine = indexes["pedidos"].as_query_engine(
                        retriever_mode="embedding",
                        response_mode="compact",
                        system_prompt=system_prompts["pedidos"]
                    )
                    response = query_engine.query(user_input)
                    print(f"Asistente: {response}\n")
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")

        # AGENTE DE FAQ (RAG)
        elif agent_choice == "faq":
            try:
                query_engine = indexes["faq"].as_query_engine(
                    retriever_mode="embedding",
                    response_mode="compact",
                    system_prompt=system_prompts["faq"]
                )
                response = query_engine.query(user_input)
                print(f"Asistente: {response}\n")
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")'''