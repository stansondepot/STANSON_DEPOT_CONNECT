import os
import json
import requests

API_TOKEN = os.environ.get('BASE_TOKEN')
INVENTORY_ID = os.environ.get('BASE_INVENTORY_ID', '112741')
url = "https://api.baselinker.com/connector.php"

def call_baselinker(method, parameters):
    payload = {"token": API_TOKEN, "method": method, "parameters": json.dumps(parameters, separators=(',', ':'))}
    return requests.post(url, data=payload).json()

try:
    print("Pobieranie produktów...")
    list_result = call_baselinker("getInventoryProductsList", {"inventory_id": int(INVENTORY_ID)})
    product_ids = [p['product_id'] for p in list_result.get('products', {}).values()]
    
    data_result = call_baselinker("getInventoryProductsData", {"inventory_id": int(INVENTORY_ID), "products": product_ids[:100]})
    
    products = []
    for p_id, p in data_result.get('products', {}).items():
        # UŻYWAMY POLA 'links' LUB 'external_url' Z BASELINKERA
        # Sprawdzamy, czy BaseLinker przekazuje gotowy link do aukcji
        allegro_url = p.get('external_url', f"https://allegro.pl/oferta/{p_id}")
        
        products.append({
            "name": p.get('text', 'Produkt'),
            "price": p.get('price', 0),
            "image": p.get('images', [''])[0],
            "url": allegro_url # Tutaj trafi teraz pełny link z Allegro
        })
            
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)
        
except Exception as e:
    print(f"Błąd: {e}")
