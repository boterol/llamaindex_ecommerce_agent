# PROYECTO FINAL 
Luis Fernando Botero

## **Fase 1: Diseño de la Arquitectura del Agente**

### **Definición de las Herramientas (Tools)**

Las herramientas implementadas dentro de la clase `Tools` son las siguientes:

1. **`evaluate_return_eligibility(order_id: str)`**
   Evalúa si un pedido específico es elegible para devolución según las políticas establecidas en el manual del taller 2 (documento utilizado como insumo del componente RAG).

   * **Entrada:** `order_id` (identificador del pedido).
   * **Salida:** Mensaje indicando si el pedido es elegible o no, junto con la justificación correspondiente (por ejemplo, días transcurridos, categoría no reembolsable o método de pago).

2. **`search_customer_orders(customer_id: str)`**
   Permite consultar todos los pedidos realizados por un cliente en el sistema.

   * **Entrada:** `customer_id` (identificador del cliente).
   * **Salida:** Listado de los pedidos asociados al cliente, con información relevante como producto, estado, fecha y valor total.

3. **`iniciar_proceso_devolucion(order_id: str, correo_cliente: str, razon: str)`**
   Inicia el proceso de devolución una vez confirmada la elegibilidad del pedido.

   * **Entrada:**

     * `order_id`: Identificador del pedido a devolver.
     * `correo_cliente`: Dirección de correo electrónico del cliente.
     * `razon`: Motivo declarado de la devolución.
   * **Salida:** Confirmación del inicio del proceso, incluyendo el número de seguimiento y una notificación simulada enviada al correo del cliente.

Estas herramientas operan sobre un **DataFrame** de pedidos que contiene las columnas:
`[order_id, customer_id, product, category, price, quantity, order_date, payment_method, estado]`.
Este dataframe simula lo que seria una fuente de datos relacional como una base de datos sql o una serie de archivos de excel. Aplicamos eso porque el ejemplo no es con muchos datos ni necesitamos mas de 1 tabla. 
Esto permite al agente acceder de forma estructurada a los datos del sistema de e-commerce para tomar decisiones y generar respuestas contextualizadas.

---

### **Selección del Marco de Agentes**

Para la implementación del agente se seleccionó **LlamaIndex** como marco de desarrollo. Esta elección se mantiene en coherencia con la decisión tomada en la **entrega anterior**, donde ya se había definido LlamaIndex como el framework base para el proyecto.

Las razones que sustentan esta elección son las siguientes:

* **Facilidad para construir agentes tipo chat:** LlamaIndex ofrece una interfaz sencilla para integrar herramientas personalizadas (*tools*) en un flujo conversacional.
* **Integración natural con RAG:** Permite vincular documentos externos, como el manual en PDF del taller 2, que contiene las políticas y reglas de devolución, facilitando la recuperación contextual de información.
* **Arquitectura modular y flexible:** Su estructura permite combinar herramientas y documentos sin requerir configuraciones complejas.
* **Escalabilidad:** LlamaIndex permite incorporar nuevas herramientas o fuentes de información en el futuro sin modificar la arquitectura general del sistema.




## **Fase 3: Análisis Crítico y Propuestas de Mejora**

El agente tiene la capacidad de realizar acciones como iniciar devoluciones o acceder a información de pedidos, lo que implica ciertos riesgos de seguridad y consideraciones éticas. Entre los principales riesgos se encuentran el uso indebido de datos personales, la ejecución no autorizada de acciones y la falta de transparencia en la toma de decisiones, que podrían afectar la privacidad y la confianza de los clientes. Para mitigarlos, se propone implementar autenticación y confirmaciones manuales antes de ejecutar acciones sensibles, limitar el acceso a datos mediante anonimización, mantener registros auditables de todas las operaciones y explicar de forma clara los criterios detrás de cada decisión. Además, se recomienda establecer un sistema de monitoreo y observabilidad con registro de acciones, alertas automáticas ante errores o comportamientos anómalos y un panel de control que permita visualizar métricas como devoluciones, errores o satisfacción del usuario. Finalmente, se plantean varias mejoras para ampliar las capacidades del agente, como crear un agente de reemplazo automático para gestionar nuevas órdenes, permitir la actualización de datos de clientes en el CRM, analizar las razones de devolución para detectar patrones y conectar el sistema con servicios externos de mensajería, pagos o logística para completar el proceso de devolución y reembolso de forma integral.


### Ejecución
Aquí tienes una guía simple y clara que puedes pegar en el README de tu repo:

---

## Cómo ejecutar el proyecto

Sigue estos pasos para levantar y usar el proyecto:

1. **Clonar el repositorio** (si no lo has hecho aún):

2. **Instalar las dependencias de Python**:

```bash
pip install -r requirements.txt
```

3. **Crear el archivo de entorno `.env`**:

En la raíz del proyecto, crea un archivo llamado `.env` con el siguiente contenido:

```env
OPENAI_API_KEY=tu_api_key_de_openai_aquí
```

> Sustituye `tu_api_key_de_openai_aquí` por tu clave real de OpenAI.

4. **Levantar Qdrant en Docker**:

El proyecto utiliza Qdrant como base de vectores. Para levantarlo, ejecuta:

```bash
docker-compose up -d
```

Esto iniciará Qdrant en un contenedor de Docker.

5. **Ejecutar el programa**:

```bash
python main.py
```

6. **Entrar a la UI desde el navegador**

Entrar a la URL 
```bash
http://localhost:7860  
```