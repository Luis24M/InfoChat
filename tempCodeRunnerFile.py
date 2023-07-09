# index
# @app.route("/")
# def index():
#     if 'user_id' in session:
#         # Usuario autenticado, redirigir al chat
#         return redirect(url_for('chatbot'))
#     else:
#         # Usuario no autenticado, mostrar la página de inicio
#         return render_template("login.html")

# # Ruta para cerrar sesión
# @app.route('/logout')
# @login_required
# def logout():
#     session.pop('user_id', None)
#     return redirect(url_for('index'))

# # chat
# @app.route("/chat")
# @login_required
# def chatbot():
#     return render_template("chat.html")

# # Ayuda
# @app.route("/ayuda")
# @login_required
# def ayuda():
#     return render_template("help.html")

# # Contacto
# @app.route("/contacto")
# @login_required
# def contacto():
#     return render_template("contact.html")