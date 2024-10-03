from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import bcrypt
from flask_cors import CORS
import jwt
import datetime
from functools import wraps

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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
    tipo_usuario = 'alunos'
    semestre = '0'

    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
    if cur.fetchone():
        return jsonify({'message': 'Este e-mail já está cadastrado!'}), 400

    hashed_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
    try:
        cur.execute('INSERT INTO usuarios (nome, email, senha, tipo_usuario, semestre) VALUES (%s, %s, %s, %s, %s)', (nome, email, hashed_senha, tipo_usuario, semestre))
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
            'alunoId': usuario[0],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, 'seu_segredo', algorithm='HS256')

        return jsonify({
            'message': f'Bem-vindo, {usuario[1]}!',
            'token': token,
            'alunoId': usuario[0],
            'tipo_usuario': usuario[4], # acessa o valor da 5° coluna da tabela usuario
            'semestre': usuario[5]
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


@app.route('/lancarnota', methods=['POST'])
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

@app.route('/lancarfaltas', methods=['POST'])
def registrar_faltas():
    data = request.get_json()
    aluno_id = data.get('aluno_id')
    disciplina = data.get('disciplina')
    dias = data.get('dias')  # Espera uma data no formato 'YYYY-MM-DD'
    
    if not aluno_id or not disciplina or not dias:
        return jsonify({'error': 'Dados incompletos.'}), 400

    cur = mysql.connection.cursor()
    try:
        cur.execute('INSERT INTO faltas (aluno_id, disciplina, dias) VALUES (%s, %s, %s)', (aluno_id, disciplina, dias))
        mysql.connection.commit()
        return jsonify({'message': 'Falta registrada com sucesso.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/lancarcertificado', methods=['POST'])
def lancar_certificado():
    data = request.get_json()
    aluno_id = data.get('aluno_id')
    tipo_certificado = data.get('tipo_certificado')
    descricao = data.get('descricao')
    ano = data.get('ano')
    instituicao = data.get('instituicao')

    if not aluno_id or not tipo_certificado or not descricao or not ano or not instituicao:
        return jsonify({"message": "Dados incompletos"}), 400

    cur = mysql.connection.cursor()
    cur.execute('''
        INSERT INTO certificados (aluno_id, tipo_certificado, descricao, ano, instituicao)
        VALUES (%s, %s, %s, %s, %s)
    ''', (aluno_id, tipo_certificado, descricao, ano, instituicao))
    
    mysql.connection.commit()
    cur.close()

    return jsonify({"message": "Certificado lançado com sucesso!"}), 201

@app.route('/certificado/<int:aluno_id>', methods=['GET'])
def obter_certificados(aluno_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM certificados WHERE aluno_id = %s', (aluno_id,))
    certificados = cur.fetchall()
    cur.close()
    
    return jsonify(certificados)

@app.route('/send-email', methods=['POST'])
def send_email():

    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    subject = data.get('subject')
    description = data.get('description')

    toaddr_support = 'ligiatrabalho9@gmail.com'
    sender_email = 'ligiatrabalho9@gmail.com'  
    sender_password = 'pzew ngbi vdrg gmmt'  

    receiver_email = email

    subject_text = f"Chamado de Suporte: {subject}"
    body_user = f"Olá {name},\n\nSeu chamado foi registrado com o seguinte assunto: '{subject}'.\nDescrição: {description}\n\nAguarde nossa resposta em breve."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['Subject'] = subject_text


    msg.attach(MIMEText(body_user, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() 
        server.login(sender_email, sender_password)

        msg['To'] = receiver_email 
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)

        msg_support = MIMEMultipart()
        msg_support['From'] = sender_email
        msg_support['To'] = toaddr_support
        msg_support['Subject'] = subject_text

        support_body = f"Novo chamado de suporte:\n\nNome: {name}\nE-mail: {email}\nAssunto: {subject}\nDescrição: {description}"
        msg_support.attach(MIMEText(support_body, 'plain'))

        server.sendmail(sender_email, toaddr_support, msg_support.as_string())

        server.quit()

        return jsonify({"success": True, "message": "E-mails enviados com sucesso!"}), 200

    except Exception as e:
        print("Erro ao enviar e-mail:", e)
        return jsonify({"success": False, "message": f"Erro ao enviar e-mail: {e}"}), 500
    
if __name__ == '__main__':
    app.run(debug=True)
