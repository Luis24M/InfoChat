from flask import Flask, redirect, render_template, request, jsonify, Response, session, url_for
from flask_login import current_user
from functools import wraps
from flask_mail import Mail, Message
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash # Para encriptar contraseñas
from flask_cors import CORS
from bson import json_util, ObjectId
# chatbot
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
# from langchain.chat_models import ChatOpenAI
# from langchain.memory import ConversationBufferMemory
# from langchain.chains import ConversationalRetrievalChain
# 
import openai
import os

# Se inicializa la app 
app = Flask(__name__)
app.secret_key = 'clave_secreta'
CORS(app)




# Conexion Base de Datos 
client=MongoClient('mongodb+srv://Luis:Lomaximoluis02@cluster0.f6yp4mn.mongodb.net/?retryWrites=true&w=majority')
db = client['InfoChat']
user_collection = db['users']
pdf_collection = db['pdfs']

# Configuración de datos para los emails 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # Puerto para SSL
app.config['MAIL_USE_TLS'] = False  # No se utiliza TLS
app.config['MAIL_USE_SSL'] = True  # Se utiliza SSL
app.config['MAIL_USERNAME'] = 'infochatunt@gmail.com'
app.config['MAIL_PASSWORD'] = 'rnuwpvlavldtjhnm'
mail = Mail(app)

# ============================================ Usuario ==========================================================

# Registrar nuevo usuario
@app.route('/register', methods=['POST'])
def register():
    username = request.json['username']
    password = request.json['password']
    email = request.json['email']
    
    if username and email and password:
        existing_user = user_collection.find_one({'username': username})
        if existing_user:
            return jsonify({'message': 'Username already exists'})
        existing_email = user_collection.find_one({'email': email})
        if existing_email:
            return jsonify({'message': 'Email already exists'})
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password
        }
        result = user_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        response = {
            'id': user_id,
            'username': username,
            'email': email
        }

        return jsonify(response)
    else:
        return jsonify({'message': 'Incomplete data'})



# Ruta para obtener los usuarios
@app.route('/users', methods=['GET'])
def get_users():
    users = user_collection.find()
    reponse = json_util.dumps(users)
    return Response(reponse, mimetype='application/json')

@app.route('/users/<id>', methods=['GET'])
def get_user(id):
    user = user_collection.find_one({'_id': ObjectId(id)})
    reponse = json_util.dumps(user)
    return Response(reponse, mimetype='application/json')

@app.route('/users/username/<username>', methods=['GET'])
def get_user_by_username(username):
    user = user_collection.find({'username': username})
    if user:
        response = json_util.dumps(user)
        return Response(response, mimetype='application/json')
    else:
        return jsonify({'message': 'User not found'})
    
    
# Ruta para verificar el inicio de sesión de un usuario
@app.route('/login', methods=['POST'])
def login_user():
    username_or_email = request.json['username_or_email']
    password = request.json['password']

    if username_or_email and password:
        user = user_collection.find_one({
            '$or': [
                {'username': username_or_email},
                {'email': username_or_email}
            ]
        })

        if user and check_password_hash(user['password'], password):
            response = {'message': 'Login successful'}
            session['user_id'] = str(user['_id'])
            session['username'] = str(user['username'])
            session['email'] = str(user['email'])

        else:
            response = {'message': 'Invalid username/email or password'}
    else:
        response = {'message': 'Incomplete data'}

    return jsonify(response)

# Decorador para verificar la autenticación del usuario
def login_required(route_function):
    @wraps(route_function)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            # Usuario autenticado, continuar con la ruta
            return route_function(*args, **kwargs)
        else:
            # Usuario no autenticado, redirigir al inicio de sesión
            return redirect(url_for('index'))
    
    return decorated_function


# =============================================================================================================================

# ===================================================== Manejo de errores =====================================================
# manejo de errores
@app.errorhandler(404)
def not_found(error=None):
    response = jsonify({
        'message': 'Resource Not Found: ' + request.url,
        'status': 404
    })
    response.status_code = 404
    return response

# ===========================================================================================================================

# ========================================================== ChatBot ========================================================
# Configuracion de Chatbot
openai.api_key = os.environ['API_KEY']
context = {"role": "system", "content": "Eres un asistente muy útil llamado InfoChat, para la  escuela de informatica de la Universidad nacional de Trujillo."}
messages = [context]

# Ruta para el chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    query = data["query"]

    messages.append({"role": "user", "content": query})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages
    )

    response_content = response.choices[0].message.content

    messages.append({"role": "assistant", "content": response_content})

    response = {    
        "message": response_content
    }

    return jsonify(response)

# Fin de configuracion de Chatbot


    

# ===============================================================================================================================

# ============================================================ Comentarios ======================================================
# Recibir comentarios
@app.route('/comments', methods=['POST'])
def create_comment():
    name = session.get('username')  # Obtener el nombre del usuario de la sesión
    email = session.get('email')  # Obtener el correo electrónico del usuario de la sesión
    comment = request.json['comment']
    estado = 'pending'
    if name and email and comment:
        comment_data = {
            'name': name,
            'email': email,
            'comment': comment,
            'status': estado
        }
        
        comment_id = db.comments.insert_one(comment_data).inserted_id
        
        msg = Message('Gracias por tu Feedback', 
                      sender=('InfoChat','InfoChat@support.com'), 
                      recipients=[email])
        msg.body = f'''Hola {name},

Hemos recibido tu mensaje: "{comment}"

Gracias por tu Feedback. Queremos que sepas que valoramos tus comentarios y nos aseguraremos de abordar cualquier problema que hayas mencionado. Si es necesario, nos comunicaremos contigo para obtener más detalles.

Atentamente,
El equipo de InfoChat'''
        mail.send(msg)

        response = {
            'id': str(comment_id),
            'name': name,
            'email': email,
            'comment': comment,
            'status': estado
        }
        
        return jsonify(response)
    else:
        return jsonify({'message': 'Invalid data'})

# =================================================================================================================

# =================================================== Rutas Html ==================================================
# index
@app.route("/")
def index():
    if 'user_id' in session:
        # Usuario autenticado, redirigir al chat
        return redirect(url_for('chatbot'))
    else:
        # Usuario no autenticado, mostrar la página de inicio
        return render_template("login.html")

# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# chat
@app.route("/chat")
@login_required
def chatbot():
    return render_template("chat.html")

# Ayuda
@app.route("/ayuda")
@login_required
def ayuda():
    return render_template("help.html")

# Contacto
@app.route("/contacto")
@login_required
def contacto():
    return render_template("contact.html")

# Procesos de login
@app.route("/registrar")
def registrar():
    return render_template("registrarse.html")

@app.route("/recuperaContraseña")
def recuperar():
    return render_template("recuperaContraseña.html")

if __name__ == "__main__":
    app.run(debug=True)
