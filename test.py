import pandas as pd
from tools import Tools

df = pd.read_csv('data/pedidos/ecommerce_orders.csv')

tools_manager = Tools(df)
tools = tools_manager.get_tools()

print(tools_manager.evaluate_return_eligibility("O0008"))  # Devuelto
print(tools_manager.evaluate_return_eligibility("O0053"))  # Sin enviar
print(tools_manager.search_customer_orders("C001"))        # Ver pedidos