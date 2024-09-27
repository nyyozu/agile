from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import bcrypt
from flask_cors import CORS
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'ciaossu12'
app.config['MYSQL_DB'] = 'sistema_faculdade'

mysql = MySQL(app)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401

        try:
            data = jwt.decode(token, 'seu_segredo', algorithms=['HS256'])
            current_user = data['email']
        except:
            return jsonify({'message': 'Token inválido!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/register', methods=['POST'])
def register():
    nome = request.json['nome']
    email = request.json['email']
    senha = request.json['senha']

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
    if cur.fetchone():
        return jsonify({'message': 'Este e-mail já está cadastrado!'}), 400

    hashed_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    try:
        cur.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, hashed_senha))
        mysql.connection.commit()
    except Exception as e:
        return jsonify({'message': 'Erro ao registrar usuário: ' + str(e)}), 500
    finally:
        cur.close()

    return jsonify({'message': 'Registro realizado com sucesso!'}), 201

@app.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    senha = request.json['senha']

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
    usuario = cur.fetchone()

    if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario[3].encode('utf-8')):
        token = jwt.encode({
            'email': email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, 'seu_segredo', algorithm='HS256')

        return jsonify({'message': f'Bem-vindo, {usuario[1]}!', 'token': token}), 200
    return jsonify({'message': 'Email ou senha inválidos!'}), 401

@app.route('/protegido', methods=['GET'])
@token_required
def protegido(current_user):
    return jsonify({'message': f'Bem-vindo, {current_user}! Este é um endpoint protegido.'})

if __name__ == '__main__':
    app.run(debug=True)