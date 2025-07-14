# -*- coding: utf-8 -*-

import os
import boto3
import uuid
import datetime
import logging
import json
from decimal import Decimal
import time 
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, PodSpec
from langchain_pinecone import PineconeEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from typing import List
import io
from PyPDF2 import PdfReader
import hashlib
from werkzeug.utils import secure_filename 

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

INDEX_NAME = "prueba1"
EMBEDDING_MODEL = "multilingual-e5-large"
EMBEDDING_DIMENSION = 1024

dynamodb = boto3.resource('dynamodb', region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
dynamo_table_name = 'MyopiaMagnaNews'
dynamo_table = dynamodb.Table(dynamo_table_name)

def save_news_record(title: str, url: str, content: str, published_date: str, source: str, keywords: list = None, categories: list = None, summary: str = None, document_hash: str = None):
    """Guarda una noticia en la tabla de DynamoDB."""
    news_id = str(uuid.uuid4())
    item = {
        'news_id': news_id,
        'title': title,
        'url': url,
        'content': content,
        'published_date': published_date,
        'source': source,
        'embeddings_generated': False
    }
    if keywords: item['keywords'] = keywords
    if categories: item['categories'] = categories
    if summary: item['summary'] = summary
    if document_hash: item['document_hash'] = document_hash
    
    try:
        dynamo_table.put_item(Item=item)
        logger.info(f"Noticia '{title}' guardada con ID: {news_id}")
        return news_id
    except Exception as e:
        logger.error(f"No se pudo guardar la noticia '{title}': {e}")
        return None

def get_all_news_from_dynamo():
    """Lee todas las noticias de la tabla de DynamoDB."""
    try:
        response = dynamo_table.scan()
        news_items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = dynamo_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            news_items.extend(response['Items'])
        def decimal_default(obj):
            if isinstance(obj, Decimal): return float(obj)
            raise TypeError(f"Objeto no serializable: {obj}")
        news_json_friendly = [json.loads(json.dumps(x, default=decimal_default)) for x in news_items]
        logger.info(f"Recuperadas {len(news_json_friendly)} noticias de DynamoDB.")
        return news_json_friendly
    except Exception as e:
        logger.error(f"Error al leer noticias de DynamoDB: {e}")
        return []


pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
embeddings_model = PineconeEmbeddings(model=EMBEDDING_MODEL, api_key=PINECONE_API_KEY)

def semantic_chunker(text: str) -> List[Document]:
    text_splitter = SemanticChunker(embeddings_model)
    return text_splitter.create_documents([text])

def setup_pinecone_index():
    """Crea el índice de Pinecone si no existe, o lo obtiene."""
    indexes = pc.list_indexes()
    indexes_names = [idx.name for idx in indexes]

    if INDEX_NAME not in indexes_names:
        logger.info(f"Creando índice Pinecone: {INDEX_NAME}...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine", 
            spec=PodSpec(environment=PINECONE_ENVIRONMENT, pod_type="s1.x1", replicas=1)
        )
        logger.info(f"Índice {INDEX_NAME} creado exitosamente.")
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)
    else:
        logger.info(f"El índice {INDEX_NAME} ya existe.")
    return pc.Index(INDEX_NAME)

pinecone_index = setup_pinecone_index()

def upsert_records_to_pinecone(records: list):
    """Sube los registros (chunks) a Pinecone en lotes."""
    BATCH_SIZE = 96
    records_batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]

    total_upserted = 0
    for i, batch_raw in enumerate(records_batches):
        try:
            formatted_batch = []
            for record in batch_raw:
                vector = embeddings_model.embed_query(record["chunk_text"])

                formatted_batch.append((record["id"], vector, {
                    "original_doc_id": record["doc_id"],
                    "chunk": record["chunk"],
                    "total_chunks": record["total_chunks"],
                    "dimension": record["dimension"],
                    "title": record.get("title", "Título Desconocido"),
                    "text": record["chunk_text"]
                }))

            pinecone_index.upsert(vectors=formatted_batch, namespace="myopia-magna-news-data")
            total_upserted += len(batch_raw)
            logger.info(f"Lote {i+1}/{len(records_batches)} subido a Pinecone. Total: {total_upserted}")
        except Exception as e:
            raise Exception(f"Fallo al subir el lote {i+1} a Pinecone: {e}")

    logger.info(f"Total de {total_upserted} records subidos a Pinecone.")

def process_single_news_item(news_item: dict):
    """
    Procesa una única noticia (diccionario con 'news_id', 'content', etc.),
    la chunkifica, la carga en Pinecone y actualiza el flag en DynamoDB.
    """
    news_doc_id = news_item.get('news_id')
    news_content = news_item.get('content')
    news_title = news_item.get('title', 'Sin Título')
    news_published_date = news_item.get('published_date')

    if not news_doc_id or not news_content or not news_published_date:
        logger.warning(f"Noticia con ID {news_doc_id} o contenido/fecha de publicación vacío. Saltando procesamiento.")
        return False

    if news_item.get('embeddings_generated', False):
        logger.info(f"Embeddings ya generados para {news_doc_id}. Saltando procesamiento.")
        return True

    try:
        chunks = semantic_chunker(news_content)
        total_chunks = len(chunks)
        if total_chunks == 0:
            logger.warning(f"No se generaron chunks para la noticia {news_doc_id}. Saltando procesamiento.")
            return False

        pinecone_upsert_records = []
        for c_idx, chunk_doc in enumerate(chunks):
            record = {
                "id": f"{news_doc_id}_c{c_idx}",
                "doc_id": news_doc_id,
                "chunk_text": chunk_doc.page_content,
                "chunk": c_idx,
                "total_chunks": total_chunks,
                "dimension": EMBEDDING_DIMENSION,
                "title": news_title
            }
            pinecone_upsert_records.append(record)

        logger.info(f"Chunks generados para {news_doc_id} ({total_chunks} chunks). Subiendo a Pinecone...")
        upsert_records_to_pinecone(pinecone_upsert_records)
        logger.info(f"Chunks de {news_doc_id} subidos exitosamente a Pinecone.")

        dynamo_table.update_item(
            Key={
                'news_id': news_doc_id,
                'published_date': news_published_date
            },
            UpdateExpression='SET embeddings_generated = :val',
            ExpressionAttributeValues={':val': True}
        )
        logger.info(f"Flag 'embeddings_generated' actualizado para {news_doc_id}.")
        return True

    except Exception as e:
        logger.error(f"Error procesando y cargando noticia {news_doc_id} a Pinecone: {e}")
        return False

def process_and_load_data_to_pinecone():
    """
    Recupera noticias de DynamoDB, las chunkifica, las carga en Pinecone
    y actualiza el flag en DynamoDB.
    """
    all_news = get_all_news_from_dynamo()
    logger.info(f"Iniciando procesamiento de {len(all_news)} noticias para Pinecone...")

    for news_item in all_news:
        if not news_item.get('embeddings_generated', False):
            process_single_news_item(news_item)
        else:
            logger.info(f"Embeddings ya generados para {news_item.get('news_id')}. Saltando.")


app = Flask(__name__)
CORS(app, origins="*") 

rag_chain = None
pinecone_vectorstore = None 

try:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY no está configurada.")
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY no está configurada.")
    if not PINECONE_ENVIRONMENT:
        raise ValueError("PINECONE_ENVIRONMENT no está configurada.")

    genai.configure(api_key=GOOGLE_API_KEY)

    embeddings_model = PineconeEmbeddings(model=EMBEDDING_MODEL, api_key=PINECONE_API_KEY)
    
    pinecone_vectorstore = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings_model,
        pinecone_api_key=PINECONE_API_KEY,
        text_key="text",
        namespace="myopia-magna-news-data"
    )

    def retrieve_relevant_chunks(query: str, k: int = 3) -> List[Document]:
        return pinecone_vectorstore.similarity_search(query, k=k)

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.7, google_api_key=GOOGLE_API_KEY)

    template = """
    Eres un asistente experto en noticias sobre miopía magna. Utiliza las siguientes piezas de contexto
    para responder a la pregunta. Si no sabes la respuesta, responde que no lo sabes,
    no intentes inventar una respuesta.

    Contexto:
    {context}

    Pregunta: {question}

    Respuesta:
    """
    prompt = PromptTemplate.from_template(template)

    def format_docs(docs: List[Document]) -> str:
        return "\n\n".join([doc.page_content for doc in docs])

    rag_chain = (
        {"context": RunnableLambda(retrieve_relevant_chunks) | RunnableLambda(format_docs),
         "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    logger.info("Chatbot backend inicializado exitosamente.")

except Exception as e:
    logger.error(f"Error fatal durante la inicialización del chatbot: {e}")

@app.route('/ask', methods=['POST'])
def ask():
    if rag_chain is None:
        logger.error("Solicitud recibida pero el chatbot no pudo inicializarse.")
        return jsonify({"error": "El servicio de chatbot no está disponible. Inténtelo más tarde."}), 500

    data = request.json
    user_question = data.get('question')

    if not user_question:
        return jsonify({"error": "Pregunta no proporcionada en el cuerpo de la solicitud JSON."}), 400

    logger.info(f"API recibida pregunta: '{user_question}'")
    try:
        response_text = rag_chain.invoke(user_question)
        logger.info(f"API respuesta generada: '{response_text}'")
        return jsonify({"answer": response_text})
    except Exception as e:
        logger.error(f"Error al procesar la pregunta del usuario con la cadena RAG: {e}")
        return jsonify({"error": "Lo siento, no pude generar una respuesta en este momento debido a un error interno."}), 500


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    logger.info("¡Petición recibida en la ruta /upload_pdf de Flask!") 
    if 'pdf_file' not in request.files:
        logger.warning("No se encontró 'pdf_file' en la solicitud.")
        return jsonify({"error": "No se proporcionó ningún archivo PDF."}), 400

    pdf_file = request.files['pdf_file']
    filename = secure_filename(pdf_file.filename)

    if not filename.endswith('.pdf'):
        logger.warning(f"Archivo no es PDF: {filename}")
        return jsonify({"error": "El archivo debe ser un PDF."}), 400

    if pdf_file.filename == '':
        logger.warning("Nombre de archivo PDF vacío.")
        return jsonify({"error": "Nombre de archivo PDF vacío."}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        try:
            pdf_binary_content = pdf_file.read()
            pdf_hash = hashlib.sha256(pdf_binary_content).hexdigest()
            logger.info(f"Hash SHA256 del PDF calculado: {pdf_hash}")
            try:
                response = dynamo_table.query(
                    IndexName='DocumentHashIndex', 
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('document_hash').eq(pdf_hash)
                )
                
                if response['Items']:
                    existing_news_id = response['Items'][0]['news_id']
                    logger.info(f"Documento con hash {pdf_hash} ya existe (news_id: {existing_news_id}).")
                    return jsonify({
                        "message": "Este documento ya ha sido procesado previamente.",
                        "news_id": existing_news_id
                    }), 200

            except Exception as e:
                logger.error(f"Error al verificar duplicados por hash en DynamoDB: {e}. Procediendo con el procesamiento.")

            pdf_reader = PdfReader(io.BytesIO(pdf_binary_content))
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() or ""

            if not full_text.strip():
                logger.warning("El archivo PDF no contiene texto extraíble.")
                return jsonify({"error": "El archivo PDF no contiene texto extraíble."}), 400

            title = os.path.splitext(pdf_file.filename)[0].replace('_', ' ').replace('-', ' ').title()
            source = "PDF Cargado"
            url = f"file_upload://{pdf_file.filename}" 
            published_date = datetime.datetime.now().isoformat()

            news_id = save_news_record(
                title=title,
                url=url,
                content=full_text,
                published_date=published_date,
                source=source,
                document_hash=pdf_hash
            )

            if news_id:
                success = process_single_news_item({
                    'news_id': news_id,
                    'title': title,
                    'url': url,
                    'content': full_text,
                    'published_date': published_date,
                    'source': source,
                    'embeddings_generated': False
                })

                if success:
                    logger.info(f"PDF '{pdf_file.filename}' procesado y cargado exitosamente. News ID: {news_id}")
                    return jsonify({"message": "PDF procesado y noticia guardada exitosamente.", "news_id": news_id}), 200
                else:
                    logger.error(f"Fallo al procesar o cargar el PDF '{pdf_file.filename}' a Pinecone.")
                    return jsonify({"error": "PDF guardado en DynamoDB, pero falló el procesamiento/carga a Pinecone."}), 500
            else:
                logger.error(f"Fallo al guardar el PDF '{pdf_file.filename}' en DynamoDB.")
                return jsonify({"error": "Fallo al guardar el PDF en la base de datos."}), 500

        except Exception as e:
            logger.error(f"Error al procesar el archivo PDF '{pdf_file.filename}': {e}")
            return jsonify({"error": f"Error interno al procesar el PDF: {str(e)}"}), 500
    else:
        logger.warning(f"Tipo de archivo no permitido o nombre de archivo no válido: {pdf_file.filename}")
        return jsonify({"error": "Solo se permiten archivos PDF."}), 400

if __name__ == '__main__':
    logger.info("Iniciando servidor Flask localmente en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)