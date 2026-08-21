import os
import json
import requests

API_TOKEN = os.environ.get('BASE_TOKEN')
INVENTORY_ID = os.environ.get('BASE_INVENTORY_ID', '112741')

url = "https://api.baselinker.com/connector.php"

# Słownik awaryjny dla specyficznych linków, jeśli zajdzie taka potrzeba
CUSTOM_LINKS = {
    "666331310": "https://allegro.pl/oferta/mercedes-benz-amg-petronas-f1-george-russell-63-brelok-breloczek-formula-1-18846738842",
    "666324970": "https://allegro.pl/oferta/mercedes-benz-amg-petronas-f1-lewis-hamilton-russell-breloki-breloczki-18846738807",
    "666331106": "https://allegro.pl/oferta/mercedes-benz-amg-petronas-f1-lewis-hamilton-44-brelok-breloczek-formula-1-18846725264"
}

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
            # 1. Filtrowanie stanu magazynowego (pomijamy wszystko <= 0)
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
            
            # 3. Pobieranie zdjęcia
            images = p.get('images', [])
            image_url = ""
            if isinstance(images, list) and images:
                image_url = images[0]
            elif isinstance(images, dict) and images:
                image_url = list(images.values())[0]
            else:
                image_url = p.get('image', '')

            # 4. Inteligentne generowanie linku do Allegro
            str_p_id = str(p_id)
            if str_p_id in CUSTOM_LINKS:
                item_url = CUSTOM_LINKS[str_p_id]
            else:
                # Spróbuj wyciągnąć pełny link z danych BaseLinkera
                # BaseLinker często przechowuje linki w polu 'links' lub 'external_url'
                links = p.get('links', {})
                # Jeśli links to słownik, szukamy czegoś co wygląda jak Allegro
                if isinstance(links, dict) and 'allegro' in links:
                    item_url = links['allegro']
                elif isinstance(links, str):
                    item_url = links
                else:
                    # Jeśli nie ma, fallback na ID aukcji, jeśli jest znane
                    allegro_id = p.get('allegro_id') or p.get('external_id')
                    if allegro_id:
                        item_url = f"https://allegro.pl/oferta/{allegro_id}"
                    else:
                        # Ostateczny fallback, jeśli nie wiemy nic
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
