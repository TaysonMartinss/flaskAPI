from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database configuration for SQL Server
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mssql+pyodbc://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}?driver=ODBC+Driver+17+for+SQL+Server"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class Pessoa(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    apelido = db.Column(db.String(32), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    nascimento = db.Column(db.Date, nullable=False)
    stack = db.Column(db.Text, nullable=True)  # Store stack as JSON string

# Helpers
def validate_payload(payload):
    if not isinstance(payload.get("apelido"), str) or len(payload["apelido"]) > 32:
        return False, "Apelido inválido."
    if not isinstance(payload.get("nome"), str) or len(payload["nome"]) > 100:
        return False, "Nome inválido."
    if not isinstance(payload.get("nascimento"), str):
        return False, "Nascimento inválido."
    try:
        stack = payload.get("stack")
        if stack is not None and not all(isinstance(item, str) and len(item) <= 32 for item in stack):
            return False, "Stack inválido."
    except TypeError:
        return False, "Stack deve ser uma lista de strings."
    return True, None


# Routes
@app.route('/pessoas', methods=['POST'])
def create_pessoa():
    data = request.get_json()
    is_valid, error = validate_payload(data)
    if not is_valid:
        return jsonify({"error": error}), 422

    try:
        new_pessoa = Pessoa(
            apelido=data["apelido"],
            nome=data["nome"],
            nascimento=data["nascimento"],
            stack=",".join(data["stack"]) if data.get("stack") else None
        )
        db.session.add(new_pessoa)
        db.session.commit()
        return make_response(jsonify({"message": "Pessoa criada com sucesso."}), 201, {"Location": f"/pessoas/{new_pessoa.id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 422


@app.route('/pessoas/<id>', methods=['GET'])
def get_pessoa(id):
    pessoa = Pessoa.query.get(id)
    if not pessoa:
        return jsonify({"error": "Pessoa não encontrada."}), 404
    return jsonify({
        "id": pessoa.id,
        "apelido": pessoa.apelido,
        "nome": pessoa.nome,
        "nascimento": pessoa.nascimento.strftime('%Y-%m-%d'),
        "stack": pessoa.stack.split(",") if pessoa.stack else None
    })


@app.route('/pessoas', methods=['GET'])
def search_pessoas():
    termo = request.args.get('t')
    if not termo:
        return jsonify({"error": "Parâmetro de busca 't' é obrigatório."}), 400

    pessoas = Pessoa.query.filter(
        db.or_(
            Pessoa.apelido.ilike(f"%{termo}%"),
            Pessoa.nome.ilike(f"%{termo}%"),
            Pessoa.stack.ilike(f"%{termo}%")
        )
    ).limit(50).all()

    return jsonify([{
        "id": pessoa.id,
        "apelido": pessoa.apelido,
        "nome": pessoa.nome,
        "nascimento": pessoa.nascimento.strftime('%Y-%m-%d'),
        "stack": pessoa.stack.split(",") if pessoa.stack else None
    } for pessoa in pessoas])


@app.route('/contagem-pessoas', methods=['GET'])
def count_pessoas():
    count = Pessoa.query.count()
    return str(count), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
