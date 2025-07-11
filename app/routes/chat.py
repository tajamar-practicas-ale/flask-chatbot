import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError
from app.models import ChatMessage, User
from app import db
from datetime import datetime
from google import genai

chat_bp = Blueprint('chat', __name__)

class ChatSchema(Schema):
    content = fields.Str(required=True)

# Inicializa el cliente Gemini
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

@chat_bp.route('/send', methods=['POST'])
@jwt_required()
def send():
    current_user = int(get_jwt_identity())
    try:
        data = ChatSchema().load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    user_input = data['content']
    # Guarda el mensaje del usuario
    user_msg = ChatMessage(user_id=current_user, role='user', content=user_input, timestamp=datetime.utcnow())
    db.session.add(user_msg)
    db.session.commit()

    # Llama a Gemini
    try:
        model = client.get_model("gemini-2.5-flash")
        response = model.generate_content(
        contents=[{"role": "user", "parts": [{"text": user_input}]}]
        )
        answer = response.candidates[0].content.parts[0].text
    except Exception as e:
        return jsonify({'msg': 'Error comunicando con Gemini', 'error': str(e)}), 502

    # Guarda la respuesta de Gemini
    assistant_msg = ChatMessage(user_id=current_user, role='assistant', content=answer, timestamp=datetime.utcnow())
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({'response': answer}), 200

@chat_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    current_user = int(get_jwt_identity())
    messages = ChatMessage.query.filter_by(user_id=current_user).order_by(ChatMessage.timestamp).all()
    history = [
        {
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        }
        for msg in messages
    ]
    return jsonify({'history': history}), 200