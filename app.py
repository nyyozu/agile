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

invalid_tokens = set()

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

    # Verifique se o usuário existe e se a senha está correta
    if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario[3].encode('utf-8')): 
        token = jwt.encode({
            'email': email,
            'alunoId': usuario[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, 'seu_segredo', algorithm='HS256')

        return jsonify({
            'message': f'Bem-vindo, {usuario[1]}!',
            'token': token,
            'alunoId': usuario[0]  # Retorna o alunoId
        }), 200

    return jsonify({'message': 'Email ou senha inválidos!'}), 401

@app.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get('Authorization').split()[1]
    
    if token in invalid_tokens:
        return jsonify({"message": "Token inválido, faça login novamente."}), 401
    
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        return jsonify({"message": "Acesso permitido!", "data": payload}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Token inválido."}), 401

@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization').split()[1]
    
    if token:
        invalid_tokens.add(token)
        return jsonify({"message": "Logout realizado com sucesso!"}), 200
    return jsonify({"message": "Token não encontrado."}), 400


@app.route('/lançar-nota', methods=['POST'])
def lancar_nota():
    data = request.get_json()
    aluno_id = data['aluno_id']
    disciplina = data['disciplina']
    nota = data['nota']

    cur = mysql.connection.cursor()

    try:
        cur.execute('INSERT INTO notas (aluno_id, disciplina, nota) VALUES (%s, %s, %s)', (aluno_id, disciplina, nota))
        mysql.connection.commit()
        return jsonify({'message': 'Nota lançada com sucesso!'}), 201
    except Exception as e:
        return jsonify({'message': 'Erro ao lançar nota: ' + str(e)}), 500
    finally:
        cur.close()

@app.route('/notas/<int:aluno_id>', methods=['GET'])
def get_notas(aluno_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute('SELECT disciplina, nota FROM notas WHERE aluno_id = %s', (aluno_id,))
        notas = cur.fetchall()
        cur.close()

        # Transformando as notas em um formato JSON
        notas_json = [{'disciplina': nota[0], 'nota': nota[1]} for nota in notas]
        return jsonify(notas_json), 200
    except Exception as e:
        print(f"Erro: {e}")  # Log do erro para depuração
        return jsonify({'error': str(e)}), 500  # Retorna erro 500

@app.route('/faltas/<int:aluno_id>', methods=['GET'])
def get_faltas(aluno_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT disciplina, COUNT(*) as total_faltas FROM faltas WHERE aluno_id = %s GROUP BY disciplina', (aluno_id,))
    faltas = cur.fetchall()
    cur.close()

    # Transformando as faltas em um formato JSON
    faltas_json = [{'disciplina': falta[0], 'total_faltas': falta[1]} for falta in faltas]
    return jsonify(faltas_json), 200

if __name__ == '__main__':
    app.run(debug=True)
