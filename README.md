# AMIRES_Chatbot

## Data Scientist & MLOps Project | Master's Final Project (TFM)

Autor: Samuel González | Proyecto: Solución de IA para AMIRES (Asociación de Miopía Magna)

## Resumen Ejecutivo

Este proyecto consiste en el diseño, desarrollo y despliegue completo de una plataforma conversacional basada en Inteligencia Artificial para la Asociación de Miopía Magna (AMIRES). El objetivo principal es proporcionar a los usuarios respuestas médicas fiables y fundamentadas sobre la patología, superando las limitaciones de los chatbots genéricos.

La solución utiliza una avanzada Arquitectura RAG (Retrieval-Augmented Generation) para asegurar la precisión y trazabilidad de la información, transformando el soporte al paciente con tecnología de Deep Learning aplicada a la Salud Digital.

## Stack Tecnológico y MLOps

La solución abarca todo el ciclo de vida del software (end-to-end), desde el desarrollo del backend hasta el despliegue en la nube y la integración con el frontend.
| Categoría |	Herramientas Clave |
|-----------|--------------------|
|Arquitectura de IA	| RAG (Retrieval-Augmented Generation), LangChain (para orchestration) |
|Lenguaje/Backend	| Python, Flask (para la API de comunicación) |
|Contenerización/DevOps |	Docker (para empaquetar y aislar el entorno) |
|Cloud/Infraestructura |	AWS EC2 (Despliegue de la API en servidor cloud) |
|Base de Conocimiento	| Archivos especializados (PDF/TXT) para grounding |
|Frontend/Integración	| WordPress (Integración mediante un plugin personalizado) |

## Arquitectura RAG Detallada

La implementación de RAG es el componente central, crucial para mantener la fiabilidad en un contexto médico:

- Ingesta de Documentos: Documentos médicos especializados sobre Miopía Magna (Base de Conocimiento).

- Vectorización: Los documentos son divididos en chunks y transformados en embeddings mediante un modelo (por ejemplo, Sentence-Transformers), y almacenados en una Base de Datos Vectorial.

- Consulta del Usuario: La pregunta del usuario se vectoriza.

- Recuperación (Retrieval): Se recuperan los chunks de información más relevantes de la base vectorial.

- Generación (Generation): Un LLM (Large Language Model) genera la respuesta final, pero condicionado a la información precisa que se le ha recuperado, asegurando la fidelidad al texto fuente.

## Despliegue en Producción

El proyecto demuestra sólidas habilidades en MLOps al llevar un modelo de IA a un entorno operativo:

- Se utilizó Docker para crear una imagen del backend (API de Flask) y de la aplicación, garantizando un entorno reproducible.

- El contenedor Docker se desplegó en una instancia AWS EC2, configurando el acceso y la seguridad necesarios.

- La comunicación entre el plugin de WordPress y la API de Flask se gestionó vía endpoints seguros.

## Impacto y Valor Añadido

- Fiabilidad Médica: Garantiza que los usuarios reciban respuestas precisas y rastreables, mitigando los riesgos de alucinación del LLM.

- Automatización de Soporte: Libera recursos humanos en la asociación al automatizar el manejo de consultas recurrentes.

- Solución End-to-End: Demuestra la capacidad de liderar un proyecto de IA desde el diseño del modelo hasta el despliegue y la integración en una plataforma web.

Para más información, consulta mi Perfil de LinkedIn: https://www.linkedin.com/in/samuel-gonzalezmartin/. 

