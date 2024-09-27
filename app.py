from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import bcrypt

app = Flask(__name__)

# Configuração do MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'ciaossu12'
app.config['MYSQL_DB'] = 'sistema_faculdade'

mysql = MySQL(app)

@app.route('/registrar', methods=['POST'])
def registrar():
    nome = request.json['nome']
    email = request.json['email']
    senha = request.json['senha']
    hashed_password = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())

    cur = mysql.connection.cursor()
    try:
        cur.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, hashed_password))
        mysql.connection.commit()
        return jsonify({'message': 'Usuário registrado com sucesso!'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    finally:
        cur.close()

@app.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    senha = request.json['senha']

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
    usuario = cur.fetchone()

    if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario[3].encode('utf-8')): 
        return jsonify({'message': f'Bem-vindo, {usuario[1]}!'}), 200  
    return jsonify({'message': 'Email ou senha inválidos!'}), 401

if __name__ == '__main__':
    app.run(debug=True)