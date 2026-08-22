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
    print("Pobieranie listy produktów z magazynu...")
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
            str_p_id = str(p_id)
            
            # 1. Filtrowanie stanu magazynowego
            stock_data = p.get('stock', {})
            total_stock = 0
            if isinstance(stock_data, dict):
                total_stock = sum(stock_data.values()) if stock_data else 0
            elif isinstance(stock_data, (int, float)):
                total_stock = stock_data

            if total_stock <= 0:
                continue

            # 2. Pobieranie ceny
            prices = p.get('prices', {})
            price = 0
            if isinstance(prices, dict) and prices:
                first_price = list(prices.values())[0]
                price = first_price if isinstance(first_price, (int, float)) else first_price.get('price', 0)
            else:
                price = p.get('price', 0)
            
            # 3. Pobieranie zdjęcia (wykorzystuje ID katalogu / p_id)
            images = p.get('images', [])
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0]
            elif isinstance(images, dict) and images:
                image_url = list(images.values())[0]
            else:
                image_url = p.get('image', '')

            # 4. WYLOWANIE 11-CYFROWEGO NUMERU OFERTY ALLEGRO
            allegro_id = None
            
            # Przeszukujemy słownik 'links' (tam BaseLinker trzyma powiązania z Allegro)
            links = p.get('links', {})
            if isinstance(links, dict):
                for market_key, market_val in links.items():
                    # market_val może być słownikiem lub bezpośrednio ID/linkiem
                    if isinstance(market_val, dict):
                        for sub_k, sub_v in market_val.items():
                            val_str = str(sub_v).strip()
                            if val_str.startswith('1') and len(val_str) >= 10:
                                allegro_id = val_str
                                break
                    else:
                        val_str = str(market_val).strip()
                        if val_str.startswith('1') and len(val_str) >= 10:
                            allegro_id = val_str
                            break
                    if allegro_id:
                        break
            
            # Jeśli nie znaleziono w links, sprawdzamy external_id oraz inne pola tekstowe
            if not allegro_id:
                for potential_field in [p.get('external_id'), p.get('sku')]:
                    if potential_field:
                        f_str = str(potential_field).strip()
                        if f_str.startswith('1') and len(f_str) >= 10:
                            allegro_id = f_str
                            break

            # Budowanie ostatecznego linku (jeśli brak 11 cyfr Allegro, awaryjnie id katalogu)
            if allegro_id:
                item_url = f"https://allegro.pl/oferta/{allegro_id}"
            else:
                item_url = f"https://allegro.pl/oferta/{str_p_id}"

            # 5. Pobieranie nazwy produktu
            text_data = p.get('text', {})
            product_name = ""
            if isinstance(text_data, dict):
                for lang_key, lang_val in text_data.items():
                    if isinstance(lang_val, dict) and 'name' in lang_val:
                        product_name = lang_val['name']
                        break
                if not product_name:
                    product_name = text_data.get('name', '')
            
            if not product_name:
                product_name = p.get('name', f"Produkt {p_id}")

            products.append({
                "name": product_name,
                "price": price,
                "image": image_url,
                "url": item_url
            })
            
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)
        
    print(f"Zapisano pomyślnie {len(products)} aktywnych produktów do pliku.")

except Exception as e:
    print(f"Błąd krytyczny: {e}")
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump([], f)
