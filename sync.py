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
    # Pobieramy oferty bezpośrednio z modułu Allegro (trwające)
    list_result = call_baselinker("getAllegroList", {
        "status": 1 # 1 oznacza trwające oferty
    })
    
    if list_result.get('status') != 'SUCCESS':
        raise Exception(f"Błąd API Allegro: {list_result}")
        
    items = list_result.get('items', [])
    products = []

    for item in items:
        # Numer oferty z Allegro (to ten długi ciąg cyfr, np. 18862598319)
        offer_id = str(item.get('oferta_id') or item.get('auction_id') or item.get('id', ''))
        
        # Jeśli API zwraca go pod innym kluczem w słowniku item:
        if not offer_id or offer_id == 'None':
            offer_id = str(item.get('basket_)-\u2026') or '') # zabezpieczenie
            
        # Spróbujmy wyciągnąć ID z różnych możliwych kluczy Allegro w BaseLinkerze
        if not offer_id.isdigit():
            # Sprawdzamy standardowe pola dla getAllegroList w BaseLinker API
            offer_id = str(item.get('id') or item.get('auction_id') or '')

        # Tytuł
        title = item.get('title') or item.get('name') or "Produkt bez nazwy"
        
        # Cena
        price = float(item.get('price', 0))
        
        # Zdjęcie
        image_url = item.get('image_url') or item.get('image', '')
        
        # Stan / Ilość w ofercie
        quantity = int(item.get('quantity', 1))
        if quantity <= 0:
            continue # Pomijamy wyprzedane

        # Generowanie linku dokładnie w formacie, którego oczekujesz
        if offer_id and offer_id.isdigit() and len(offer_id) > 5:
            item_url = f"https://allegro.pl/oferta/{offer_id}"
        else:
            item_url = "https://allegro.pl"

        products.append({
            "name": title,
            "price": price,
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
