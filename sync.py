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
            
            # 1. Filtrowanie stanu magazynowego (odrzucamy <= 0)
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
                if isinstance(first_price, (int, float)):
                    price = first_price
                elif isinstance(first_price, dict):
                    price = first_price.get('price', 0)
            else:
                price = p.get('price', 0)
            
            # 3. Pobieranie zdjęcia
            images = p.get('images', [])
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0]
            elif isinstance(images, dict) and images:
                image_url = list(images.values())[0]
            else:
                image_url = p.get('image', '')

            # 4. Wyciąganie numeru oferty Allegro ze słownika links
            allegro_offer_id = None
            links = p.get('links', {})
            
            if isinstance(links, dict):
                for market_key, market_val in links.items():
                    # Szukamy powiązań z Allegro (klucze zazwyczaj zawierają 'allegro' lub ID konta)
                    if isinstance(market_val, dict):
                        # Czasami ID oferty jest ukryte jako listing_id, external_id lub id wewnątrz słownika
                        for sub_k in ['listing_id', 'external_id', 'id', 'auction_id']:
                            val = market_val.get(sub_k)
                            if val and str(val).isdigit() and len(str(val)) > 8:
                                allegro_offer_id = str(val)
                                break
                    elif market_val and str(market_val).isdigit() and len(str(market_val)) > 8:
                        allegro_offer_id = str(market_val)
                        break
                    if allegro_offer_id:
                        break

            # Jeśli nie znaleziono w links, sprawdzamy pole external_id / allegro_id na poziomie produktu
            if not allegro_offer_id:
                for field in ['external_id', 'allegro_id']:
                    val = str(p.get(field, ''))
                    if val.isdigit() and len(val) > 8:
                        allegro_offer_id = val
                        break

            # Budowanie poprawnego linku z numerem oferty Allegro
            if allegro_offer_id:
                item_url = f"https://allegro.pl/oferta/{allegro_offer_id}"
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
