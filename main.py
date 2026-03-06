import jwt
from jwt.exceptions import DecodeError
from functools import wraps
from flask import Flask, jsonify, request, make_response
import requests
import os
#import psycopg2
from dotenv import load_dotenv
from datetime import datetime
from flasgger import Swagger, swag_from
from flask_restful import Api, Resource
import sqlite3



load_dotenv()

app = Flask(__name__)
api = Api(app)

# Swagger config
app.config['SWAGGER'] = {
    'title': 'Livraison Service API',
    'uiversion': 3,
    'openapi': '3.0.2'
}

swagger = Swagger(app)

app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

AUTH_SERVICE_URL =  os.environ.get("AUTH_SERVICE_URL")
VENTE_SERVICE_URL =  os.environ.get("VENTE_SERVICE_URL")


# connexion DB
# def get_db_connection():
#     conn = psycopg2.connect(
#         host=os.environ['DB_HOST'],
#         database='livraison',
#         user=os.environ['DB_USERNAME'],
#         password=os.environ['DB_PASSWORD']
#     )
#     return conn


def get_db_connection():
    conn = sqlite3.connect("livraison.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS livraison (
            id_livraison INTEGER PRIMARY KEY AUTOINCREMENT,
            id_utilisateur INTEGER,
            id_vente INTEGER,
            date_livre TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()



def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        
        token = request.cookies.get("token") or request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401

        
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        try:
            
            data = jwt.decode(token, "SECRET_KEY_PARTAGE_AVEC_AUTH", algorithms=["HS256"])
            current_user_id = data["id"]
        except DecodeError:
            return jsonify({"error": "Invalid token"}), 401

       
        return f(current_user_id, *args, **kwargs)

    return decorated


# LOGIN RESOURCE
class LoginResource(Resource):

    @swag_from({
        'tags': ['Auth'],
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {
                    'example': {
                        "username": "admin",
                        "password": "1234"
                    }
                }
            }
        },
        'responses': {
            200: {
                'description': 'Login successful',
                'content': {
                    'application/json': {
                        'example': {
                            "token": "jwt_token_here"
                        }
                    }
                }
            },
            401: {
                'description': 'Invalid credentials'
            }
        }
    })
    def post(self):
        pass

    #     data = request.get_json()

    #     response = requests.post(
    #         url_auth,
    #         json={
    #             "username": data["username"],
    #             "password": data["password"]
    #         }
    #     )

    #     if response.status_code != 200:
    #         return {"error": "Invalid credentials"}, 401

    #     token = response.json()["token"]

    #     flask_response = make_response(response.json())
    #     #flask_response.set_cookie("token", token)

    #     return flask_response


# CREER LIVRAISON
class LivrerResource(Resource):

    @swag_from({
        'tags': ['Livraisons'],
        'parameters': [
            
            {
                'name': 'vente_id',
                'in': 'path',
                'required': True,
                'schema': {
                    'type': 'integer'
                },
                'example': 1
            },
            
           
        ],
        'responses': {
            200: {
                'description': 'Livraison créée',
                'content': {
                    'application/json': {
                        'example': {
                            "message": "Livraison enregistrée avec succès"
                        }
                    }
                }
            }
        }
    })
    #@token_required
    def post(self, vente_id):

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO livraison (id_utilisateur, id_vente, date_livre)
            VALUES (?, ?, ?)
        """, (
            1,
            vente_id,
            datetime.now()
        ))

        conn.commit()

        cur.close()
        conn.close()

        return {
            "message": "Livraison enregistrée avec succès"
        }


# MES LIVRAISONS
class MesLivraisonsResource(Resource):

    @swag_from({
        'tags': ['Livraisons'],
        'responses': {
            200: {
                'description': 'Liste des livraisons utilisateur',
                'content': {
                    'application/json': {
                        'example': [
                            {
                                "id_livraison": 1,
                                "id_vente": 5,
                                "date_livre": "2026-03-02T10:00:00"
                            }
                        ]
                    }
                }
            }
        }
    })
    @token_required
    def get(self, current_user_id):

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id_livraison, id_vente, date_livre
            FROM livraison
            WHERE id_utilisateur = ?
            ORDER BY date_livre DESC
        """, (current_user_id,))


        rows = cur.fetchall()

        cur.close()
        conn.close()

        livraisons = []

        for row in rows:
            livraisons.append({
                "id_livraison": row[0],
                "id_vente": row[1],
                "date_livre": str(row[2])
            })

        return livraisons


# TOUTES LES LIVRAISONS
class AllLivraisonsResource(Resource):

    @swag_from({
        'tags': ['Livraisons'],
        'responses': {
            200: {
                'description': 'Liste complète',
                'content': {
                    'application/json': {
                        'example': [
                            {
                                "id_livraison": 1,
                                "id_utilisateur": 1,
                                "id_vente": 5,
                                "date_livre": "2026-03-02T10:00:00"
                            }
                        ]
                    }
                }
            }
        }
    })
    #@token_required
    def get(self):

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id_livraison, id_utilisateur, id_vente, date_livre
            FROM livraison
            ORDER BY date_livre DESC
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        livraisons = []

        for row in rows:

            #livraison_id, vente_id, date_livre = row[0], row[2], row[3]

            # Appel service ventes
            #vente_resp = requests.get(f"{VENTE_SERVICE_URL}/{vente_id}")
            #vente_info = vente_resp.json() if vente_resp.status_code == 200 else {"error": "vente introuvable"}

            # Appel service auth pour l'utilisateur
            #user_resp = requests.get(f"{AUTH_SERVICE_URL}/{row[1]}")
            #user_info = user_resp.json() if user_resp.status_code == 200 else {"error": "utilisateur introuvable"}

            livraisons.append({
                "id_livraison": row[0],
                "utilisateur": row[1],
                "vente": row[2],
                "date_livre": str(row[3])
            })

        return livraisons


# REGISTER RESOURCES
#api.add_resource(LoginResource, "/login")
api.add_resource(LivrerResource, "/livrer/<int:vente_id>")
api.add_resource(MesLivraisonsResource, "/mes_livraisons")
api.add_resource(AllLivraisonsResource, "/livraisons")


if __name__ == "__main__":
    app.run(debug=True)
