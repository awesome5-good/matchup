from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('matchup.html')

@app.route('/matchup.html')
def matchup():
    return app.send_static_file('matchup.html')

@app.route('/api/claude', methods=['POST'])
def claude_proxy():
    data = request.json
    api_key = data.get('api_key', '')
    payload = data.get('payload', {})

    if not api_key:
        return jsonify({'error': 'API 키가 없습니다'}), 400

    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        },
        json=payload,
        timeout=60
    )

    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    print('매치업 서버 시작: http://localhost:8080')
    app.run(port=8080, debug=False)
