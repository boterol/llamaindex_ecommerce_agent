import datetime
import pandas as pd
from llama_index.core.tools import FunctionTool
import os
from dotenv import load_dotenv



class Tools:
    """Colección de tools relacionadas con devoluciones para e-commerce ecológico."""
    
    def __init__(self, pedidos_df: pd.DataFrame):
        load_dotenv()
        """
        pedidos_df: DataFrame con columnas:
        [order_id, customer_id, product, category, price, quantity, order_date, payment_method, estado]
        """
        self.df = pedidos_df.copy()
        # Normalizamos los nombres de columnas y texto
        self.df.columns = [c.lower().strip() for c in self.df.columns]
        self.df["product"] = self.df["product"].astype(str).str.lower().str.strip()
        self.df["category"] = self.df["category"].astype(str).str.lower().str.strip()
        self.df["estado"] = self.df["estado"].astype(str).str.lower().str.strip()
        
        # Convertir order_date a datetime
        self.df["order_date"] = pd.to_datetime(self.df["order_date"])
    
    def evaluate_return_eligibility(self, order_id: str) -> str:
        """
        Evalúa si un pedido es elegible para devolución usando el order_id.
        
        Args:
            order_id: ID del pedido (ej: 'O0001')
        
        Returns:
            Mensaje indicando si es elegible o no, y las razones.
        """
        order_id = order_id.upper().strip()
        
        # Filtramos el pedido correspondiente
        pedido = self.df[self.df["order_id"] == order_id]
        
        if pedido.empty:
            return f"❌ No se encontró el pedido {order_id} en el sistema."
        
        pedido = pedido.iloc[0]
        
        # 1. Verificar estado del pedido
        estado = pedido["estado"]
        if estado == "devuelto":
            return f"❌ El pedido {order_id} ya fue devuelto anteriormente."
        
        if estado == "sin enviar":
            return f"⚠️ El pedido {order_id} aún no ha sido enviado. Puedes cancelarlo sin iniciar una devolución."
        
        if estado == "enviado":
            return f"⚠️ El pedido {order_id} está en tránsito. Espera a recibirlo para iniciar una devolución si es necesario."
        
        # 2. Categoría no elegible para devolución
        categoria = pedido["category"]
        categorias_no_devolucion = ["higiene", "software", "tarjetas de regalo"]
        
        if categoria in categorias_no_devolucion:
            return (
                f"❌ El producto '{pedido['product']}' pertenece a la categoría '{categoria}', "
                f"que no admite devoluciones por política de la tienda."
            )
        
        # 3. Días desde la compra
        order_date = pedido["order_date"].date()
        days_since_order = (datetime.date.today() - order_date).days
        
        if days_since_order > 30:
            return (
                f"❌ Han pasado {days_since_order} días desde la compra (fecha: {order_date}). "
                f"Solo se admiten devoluciones dentro de 30 días."
            )
        
        # 4. Productos personalizados requieren revisión
        if categoria == "personalizado":
            return (
                f"⚠️ El producto '{pedido['product']}' es personalizado. "
                f"La devolución requiere revisión manual del equipo. "
                f"Tiempo desde compra: {days_since_order} días."
            )
        
        # 5. Método de pago efectivo requiere revisión
        payment_method = str(pedido["payment_method"]).lower()
        if payment_method == "efectivo":
            return (
                f"✅ Pedido {order_id} elegible para devolución, pero requiere revisión manual "
                f"por haber sido pagado en efectivo. Producto: '{pedido['product']}'. "
                f"Tiempo desde compra: {days_since_order} días."
            )
        
        # 6. Elegible sin restricciones
        return (
            f"✅ El pedido {order_id} con producto '{pedido['product']}' "
            f"es elegible para devolución. "
            f"Tiempo desde compra: {days_since_order} días. "
            f"Método de pago: {pedido['payment_method']}. "
            f"Total a reembolsar: ${pedido['price'] * pedido['quantity']:,.0f} COP."
        )
    
    def search_customer_orders(self, customer_id: str) -> str:
        """
        Busca todos los pedidos de un cliente específico.
        
        Args:
            customer_id: ID del cliente (ej: 'C001')
        
        Returns:
            Lista de pedidos del cliente con información relevante.
        """
        customer_id = customer_id.upper().strip()
        
        pedidos = self.df[self.df["customer_id"] == customer_id]
        
        if pedidos.empty:
            return f"❌ No se encontraron pedidos para el cliente {customer_id}."
        
        result = f"📦 Pedidos del cliente {customer_id}:\n\n"
        
        for _, pedido in pedidos.iterrows():
            days_ago = (datetime.date.today() - pedido["order_date"].date()).days
            total = pedido["price"] * pedido["quantity"]
            
            result += (
                f"• Order ID: {pedido['order_id']}\n"
                f"  Producto: {pedido['product']}\n"
                f"  Estado: {pedido['estado']}\n"
                f"  Total: ${total:,.0f} COP\n"
                f"  Fecha: {pedido['order_date'].date()} (hace {days_ago} días)\n\n"
            )
        
        return result
    
    def initiate_return_request(self, order_id: str, customer_email: str, reason: str) -> str:
        """
        Inicia el proceso de solicitud de devolución enviando un email.
        
        Args:
            order_id: ID del pedido (ej: 'O0001')
            customer_email: Email del cliente
            reason: Motivo de la devolución
        
        Returns:
            Confirmación del envío del email o mensaje de error.
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        order_id = order_id.upper().strip()
        
        # Verificar que el pedido existe
        pedido = self.df[self.df["order_id"] == order_id]
        
        if pedido.empty:
            return f"❌ No se encontró el pedido {order_id} en el sistema."
        
        pedido = pedido.iloc[0]
        
        # Verificar elegibilidad básica antes de enviar email
        estado = pedido["estado"]
        if estado != "recibido":
            return f"❌ El pedido {order_id} no está en estado 'recibido'. Estado actual: {estado}. No se puede iniciar devolución."
        
        categoria = pedido["category"]
        categorias_no_devolucion = ["higiene", "software", "tarjetas de regalo"]
        
        if categoria in categorias_no_devolucion:
            return f"❌ El producto pertenece a la categoría '{categoria}' que no admite devoluciones."
        
        order_date = pedido["order_date"].date()
        days_since_order = (datetime.date.today() - order_date).days
        
        if days_since_order > 30:
            return f"❌ Han pasado {days_since_order} días desde la compra. Fuera del plazo de 30 días."
        
        # Preparar datos del email
        total = pedido["price"] * pedido["quantity"]
        
        # Configuración SMTP de Gmail 
        # Para usar esta función, necesitas:
        # 1. Una cuenta de Gmail
        # 2. Activar "Contraseñas de aplicación" en tu cuenta Google
        # 3. Configurar las variables de entorno o pasar credenciales
        
        try:
            # Email de la tienda (configurar según tu email)
            sender_email = os.getenv("EMAIL")
            sender_password = os.getenv("PASSWORD")  
            
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = customer_email
            msg['Subject'] = f"Solicitud de Devolución - Pedido {order_id}"
            
            # Cuerpo del email en HTML
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
                        <div style="background-color: #2e7d32; color: white; padding: 20px; text-align: center;">
                            <h1>🌱 ECOMARKET </h1>
                        </div>
                        
                        <div style="background-color: white; padding: 30px; margin-top: 20px;">
                            <h2 style="color: #2e7d32;">Solicitud de Devolución Recibida</h2>
                            
                            <p>Hemos recibido tu solicitud de devolución para el siguiente pedido:</p>
                            
                            <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #2e7d32; margin: 20px 0;">
                                <p><strong>Número de Pedido:</strong> {order_id}</p>
                                <p><strong>Producto:</strong> {pedido['product'].title()}</p>
                                <p><strong>Cantidad:</strong> {pedido['quantity']}</p>
                                <p><strong>Total:</strong> ${total:,.0f} COP</p>
                                <p><strong>Fecha de compra:</strong> {order_date}</p>
                                <p><strong>Motivo:</strong> {reason}</p>
                            </div>
                            
                            <h3 style="color: #2e7d32;">Próximos pasos:</h3>
                            <ol>
                                <li>Nuestro equipo revisará tu solicitud en las próximas 24-48 horas</li>
                                <li>Recibirás un email con las instrucciones de envío</li>
                                <li>Una vez recibamos el producto, procesaremos tu reembolso</li>
                            </ol>
                            
                            <p style="margin-top: 30px;">Si tienes alguna pregunta, responde a este email o contacta con nuestro servicio al cliente.</p>
                            
                            <p style="margin-top: 20px; color: #666; font-size: 14px;">
                                <strong>Nota:</strong> El producto debe estar sin usar y en su empaque original.
                            </p>
                        </div>
                        
                        <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                            <p>© 2025 E-commerce Ecológico - Comprometidos con el planeta 🌍</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Adjuntar HTML al mensaje
            msg.attach(MIMEText(html_body, 'html'))
            
            # Enviar email usando Gmail SMTP
            # NOTA: Para producción, considera usar servicios como SendGrid, Mailgun o Amazon SES
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return (
                f"✅ Solicitud de devolución iniciada exitosamente!\n\n"
                f"📧 Se ha enviado un email de confirmación a: {customer_email}\n"
                f"📦 Pedido: {order_id}\n"
                f"🛍️ Producto: {pedido['product']}\n"
                f"💰 Monto a reembolsar: ${total:,.0f} COP\n\n"
                f"Nuestro equipo revisará tu solicitud en 24-48 horas."
            )
            
        except smtplib.SMTPAuthenticationError:
            return (
                "⚠️ Error de autenticación de email. "
                "La solicitud fue registrada pero no se pudo enviar el email de confirmación. "
                "Nuestro equipo se pondrá en contacto contigo."
            )
        except Exception as e:
            return (
                f"⚠️ La solicitud fue registrada pero hubo un problema al enviar el email: {str(e)}\n"
                f"Pedido {order_id} marcado para revisión. "
                f"Te contactaremos a {customer_email} en las próximas horas."
            )
    
    # === ENVOLVER EN FUNCTIONTOOL ===
    def get_tools(self):
        """Devuelve las tools listas para conectar al agente."""
        return [
            FunctionTool.from_defaults(
                fn=self.evaluate_return_eligibility,
                name="evaluate_return_eligibility",
                description=(
                    "Evalúa si un pedido es elegible para devolución usando el order_id. "
                    "Verifica estado, categoría, tiempo desde compra y método de pago. "
                    "Usa esta tool cuando el usuario pregunte si puede devolver un pedido específico."
                ),
            ),
            FunctionTool.from_defaults(
                fn=self.search_customer_orders,
                name="search_customer_orders",
                description=(
                    "Busca todos los pedidos de un cliente usando su customer_id. "
                    "Útil cuando el usuario no sabe su order_id pero sí su customer_id, "
                    "o cuando quiere ver su historial de compras."
                ),
            ),
            FunctionTool.from_defaults(
                fn=self.initiate_return_request,
                name="initiate_return_request",
                description=(
                    "ESTA TOOL PUEDE SER USADA UNICAMENTE CUANDO YA SE EVALUO QUE LA DEVOLUCION SI PUEDE HACERCE "
                    "Inicia una solicitud de devolución enviando un email de confirmación al cliente. "
                    "Requiere order_id, email del cliente y motivo de la devolución. "
                    "Usa esta tool después de verificar elegibilidad con evaluate_return_eligibility."
                ),
            ),
        ]