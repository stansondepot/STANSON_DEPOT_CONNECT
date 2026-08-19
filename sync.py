import os
import json
import requests

API_TOKEN = os.environ.get('BASE_TOKEN')
INVENTORY_ID = os.environ.get('BASE_INVENTORY_ID', '112741')

url = "https://api.baselinker.com/connector.php"

def call_baselinker(method, parameters):
    payload = {
        "token": API_TOKEN,
        "method": method,
        "parameters": json.dumps(parameters, separators=(',', ':'))
    }
    response = requests.post(url, data=payload)
    return response.json()

try:
    print("Pobieranie listy produktów...")
    list_result = call_baselinker("getInventoryProductsList", {
        "inventory_id": int(INVENTORY_ID),
        "page": 1
    })
    
    if list_result.get('status') != 'SUCCESS':
        raise Exception(f"Błąd API listy: {list_result}")
        
    items = list_result.get('products', {})
    product_ids = list(items.keys()) if isinstance(items, dict) else [p.get('product_id') for p in items]
    
    if not product_ids:
        print("Brak produktów w magazynie.")
        products = []
    else:
        print(f"Pobieranie szczegółów dla {len(product_ids)} produktów...")
        data_result = call_baselinker("getInventoryProductsData", {
            "inventory_id": int(INVENTORY_ID),
            "products": product_ids[:100]
        })
        
        products = []
        detailed_items = data_result.get('products', {})
        
        for p_id, p in detailed_items.items():
            prices = p.get('prices', {})
            price = 0
            if isinstance(prices, dict) and prices:
                first_price = list(prices.values())[0]
                price = first_price if isinstance(first_price, (int, float)) else first_price.get('price', 0)
            else:
                price = p.get('price', 0)
            
            images = p.get('images', [])
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0]
            elif isinstance(images, dict) and images:
                image_url = list(images.values())[0]
            else:
                image_url = p.get('image', '')

            # Próba wyciągnięcia pełnego linku Allegro z pól BaseLinkera
            links = p.get('links', {})
            item_url = ""
            if isinstance(links, dict):
                for key, val in links.items():
                    if 'allegro' in str(val).lower():
                        item_url = val
                        break
            
            if not item_url:
                item_url = p.get('url', f"https://allegro.pl/oferta/{p_id}")

            # Pobieranie nazwy produktu
            name_data = p.get('text', '')
            if isinstance(name_data, dict):
                product_name = name_data.get('name', '')
            else:
                product_name = str(name_data)

            products.append({
                "name": product_name,
                "price": price,
                "image": image_url,
                "url": item_url
            })
            
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)
        
    print(f"Zapisano pomyślnie {len(products)} produktów.")

except Exception as e:
    print(f"Błąd krytyczny: {e}")
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump([], f)
