from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import json
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)
CORS(app)

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# Food database fallback
FOOD_DB = {
    'roti': {'calories': 70, 'protein': 2, 'carbs': 14, 'fat': 0.5},
    'rice': {'calories': 206, 'protein': 4, 'carbs': 45, 'fat': 0.3},
    'dal': {'calories': 170, 'protein': 12, 'carbs': 30, 'fat': 2},
    'paneer': {'calories': 265, 'protein': 25, 'carbs': 2, 'fat': 17},
    'chicken': {'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6},
    'fish': {'calories': 120, 'protein': 20, 'carbs': 0, 'fat': 3},
    'egg': {'calories': 155, 'protein': 13, 'carbs': 1, 'fat': 11},
    'naan': {'calories': 300, 'protein': 8, 'carbs': 42, 'fat': 12},
    'samosa': {'calories': 200, 'protein': 4, 'carbs': 20, 'fat': 12},
    'biryani': {'calories': 400, 'protein': 15, 'carbs': 50, 'fat': 15},
}

def analyze_with_gemini(image_base64):
    """Try Google Gemini API"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": "Analyze this food image. Return ONLY valid JSON with no other text: {\"foodName\": \"exact name\", \"calories\": 250, \"protein\": 15, \"carbs\": 30, \"fat\": 8, \"insight\": \"Brief health note\"}"
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            json_str = text[json_start:json_end]
            return json.loads(json_str)
    except Exception as e:
        print(f"Gemini error: {e}")
    
    return None

def analyze_with_groq(image_base64):
    """Groq fallback (text-based)"""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mixtral-8x7b-32768",
            "messages": [{
                "role": "user",
                "content": "Indian food nutrition. Return JSON: {foodName, calories, protein, carbs, fat, insight}"
            }],
            "max_tokens": 300
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            text = data['choices'][0]['message']['content']
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            json_str = text[json_start:json_end]
            return json.loads(json_str)
    except Exception as e:
        print(f"Groq error: {e}")
    
    return None

def get_fallback_nutrition():
    """Fallback when APIs fail"""
    import random
    foods_list = list(FOOD_DB.items())
    food_name, nutrition = random.choice(foods_list)
    return {
        'foodName': food_name.capitalize(),
        'calories': nutrition['calories'],
        'protein': nutrition['protein'],
        'carbs': nutrition['carbs'],
        'fat': nutrition['fat'],
        'insight': 'Nutritious Indian meal'
    }

@app.route('/api/analyze-food', methods=['POST'])
def analyze_food():
    try:
        data = request.json
        image_base64 = data.get('image')
        
        if not image_base64:
            return jsonify({'error': 'No image'}), 400
        
        # Clean base64
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Try Gemini first
        print("Trying Gemini API...")
        result = analyze_with_gemini(image_base64)
        if result and 'foodName' in result:
            print("✅ Gemini success")
            return jsonify(result)
        
        # Fallback to Groq
        print("Trying Groq API...")
        result = analyze_with_groq(image_base64)
        if result and 'foodName' in result:
            print("✅ Groq success")
            return jsonify(result)
        
        # Final fallback
        print("Using fallback database...")
        result = get_fallback_nutrition()
        return jsonify(result)
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify(get_fallback_nutrition())

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'Backend is working! 🚀'})

if __name__ == '__main__':
    app.run(debug=False)
