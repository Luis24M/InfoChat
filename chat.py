from flask import Flask, redirect, render_template, request, jsonify, Response, session, url_for, send_from_directory
from flask_login import current_user
from functools import wraps
from flask_mail import Mail, Message
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash # Para encriptar contraseñas
from flask_cors import CORS
from bson import json_util, ObjectId
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
# chatbot
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
# 
import ssl
import openai
import os


# Cargar variables de entorno desde el archivo .env
load_dotenv()


# Se inicializa la app 
app = Flask(__name__)
app.secret_key = 'clave_secreta'
CORS(app)


# Conexion Base de Datos 
""" context = ssl._create_unverified_context()
print(ssl.get_default_verify_paths()) """
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
client = MongoClient('mongodb+srv://Luis:Lomaximoluis02@cluster0.f6yp4mn.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true')
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

app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Ruta de la carpeta "uploads"


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
            'password': hashed_password,
            'role': 'user'
        }
        result = user_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        response = {
            'id': user_id,
            'username': username,
            'email': email,
            'role': 'user' 
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
            session['role'] = str(user['role'])

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

# Decorador para verificar si el usuario es administrador
def admin_required(route_function):
    @wraps(route_function)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session and session['role'] == 'admin':
            # Usuario autenticado y es administrador, continuar con la ruta
            return route_function(*args, **kwargs)
        else:
            # Usuario no autenticado o no es administrador, redirigir a una página de acceso denegado
            return redirect(url_for('access_denied'))
    
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

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    # tengo mi api_key en un archivo .env variable
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('API_KEY'))
    #embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    llm = ChatOpenAI(openai_api_key=os.getenv('API_KEY'),
                     temperature=0.1,)
    print(llm.temperature)
    memory = ConversationBufferMemory(
        memory_key='chat_history',
        return_messages=True
    )
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

# La lista debe contener los nombres de los archivos PDF que se encuentran en la carpeta "statics/uploads"
# Cargar de manera automatica los pdfs de static/uploads a pdf_docs
def cargar_pdfs():
    global pdf_docs
    pdf_docs = []
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        if file.endswith('.pdf'):
            pdf_docs.append(os.path.join(app.config['UPLOAD_FOLDER'], file))

def run_chatbot():
    cargar_pdfs()
    text = get_pdf_text(pdf_docs)
    text_chunks = get_text_chunks(text)
    vectorstore = get_vectorstore(text_chunks)
    conversation_chain = get_conversation_chain(vectorstore)
    return conversation_chain

conversation_chain = run_chatbot()

def recargar_chatbot():
    global conversation_chain
    conversation_chain = run_chatbot()
    
@app.route('/reload_chatbot', methods=['POST'])
@admin_required
def reload_chatbot():
    recargar_chatbot()
    return redirect(url_for('admin_dashboard'))

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data["query"]
    
    

    response = {
        "message":conversation_chain({'question': user_input})['answer']
    }
    
    return jsonify(response)

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


# =================================================== PDF =========================================================
# Ruta para subir PDFs
@app.route('/upload_pdf', methods=['POST'])
@admin_required
def upload_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({'message': 'No file selected'}), 400
    
    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
    
    # Guardar el archivo PDF en la carpeta "uploads"
    filename = secure_filename(pdf_file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    pdf_file.save(filepath)
    
    # Guardar el registro del PDF en la base de datos si es necesario
    # ...
    #guardar Id del usuario que subio el pdf
    id_user = ObjectId(session.get('user_id'))
    # nombre del pdf
    pdf_name = request.form.get('pdf_name')
    # ruta del pdf
    pdf_path = filepath
    # guardar en la base de datos
    
    pdf_data = {
        'id_user': id_user,
        'pdf_name': pdf_name,
        'pdf_path': pdf_path
    }
    
    pdf_collection.insert_one(pdf_data)
    
    return jsonify({'message': 'PDF uploaded successfully'}), 200

@app.route('/pdfs/<filename>')
def download_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/assign_role', methods=['POST'])
@admin_required
def assign_role():
    user_id_str = request.form.get('user_id')
    role = request.form.get('role')
    
    try:
        user_id = ObjectId(user_id_str)
    except:
        return jsonify({'message': 'Invalid user_id format'}), 400
    
    # Verificar si el usuario existe en la base de datos
    user = user_collection.find_one({'_id': user_id})
    if user:
        # Actualizar el rol del usuario
        user_collection.update_one({'_id': user_id}, {'$set': {'role': role}})
        return jsonify({'message': 'Role assigned successfully'}), 200
    else:
        return jsonify({'message': 'User not found'}), 404


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

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Vista del panel de administración
    users = user_collection.find()
    return render_template('admin_dashboard.html', users=users)

@app.route('/access-denied')
def access_denied():
    return render_template('access_denied.html')


if __name__ == "__main__":
    app.run(debug=True, port=2000)
