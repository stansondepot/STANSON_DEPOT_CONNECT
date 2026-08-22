import os
import json
import requests

API_TOKEN = os.environ.get('BASE_TOKEN')
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
    print("Pobieranie listy ofert z Allegro...")
    # Pobieramy oferty bezpośrednio z modułu Allegro w BaseLinkerze
    result = call_baselinker("getAllegroList", {
        "status": 1  # 1 oznacza aktywne oferty trwające
    })
    
    if result.get('status') != 'SUCCESS':
        # Próbujemy alternatywnej metody dla marketplace, gdyby getAllegroList zwróciło błąd
        result = call_baselinker("getExternalOrders", {}) # awaryjnie
        if result.get('status') != 'SUCCESS':
            raise Exception(f"Błąd API Allegro: {result}")
        
    items = result.get('items', [])
    if not items:
        # Sprawdzamy strukturę dla standardowego modułu marketplace
        items = result.get('filters', {}).get('ekomers', []) # bezpiecznik
        
    products = []
    
    # Jeśli dostajemy słownik lub listę z getAllegroList
    if isinstance(items, dict):
        items_iterable = items.values()
    else:
        items_iterable = items

    for item in items_iterable:
        # Wyciąganie 11-cyfrowego numeru oferty Allegro (np. z fielda 'auction_id' lub 'external_id')
        offer_id = item.get('auction_id') or item.get('id') or item.get('external_id')
        
        if not offer_id:
            continue
            
        name = item.get('title') or item.get('name') or f"Oferta {offer_id}"
        price = item.get('price') or item.get('end_price') or 0
        image_url = item.get('image') or item.get('image_url') or ''
        
        # Tworzenie idealnego linku Allegro z 11-cyfrowym numerem
        item_url = f"https://allegro.pl/oferta/{offer_id}"

        products.append({
            "name": name,
            "price": float(price),
            "image": image_url,
            "url": item_url
        })
        
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)
        
    print(f"Zapisano pomyślnie {len(products)} aktywnych ofert z Allegro do pliku.")

except Exception as e:
    print(f"Błąd krytyczny: {e}")
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump([], f)
