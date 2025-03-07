from flask import Flask, request, jsonify
import requests
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    @app.route("/api/users/register", methods=["POST"])
    def register():
        return proxy_request("POST", "/api/users/register")

    @app.route("/api/users/login", methods=["POST"])
    def login():
        return proxy_request("POST", "/api/users/login")

    @app.route("/api/users/profile", methods=["GET"])
    def get_profile():
        return proxy_request("GET", "/api/users/profile")

    @app.route("/api/users/profile", methods=["PUT"])
    def update_profile():
        return proxy_request("PUT", "/api/users/profile")

    def proxy_request(method, path):
        url = f"{app.config['USER_SERVICE_URL']}{path}"

        headers = {key: value for key, value in request.headers if key != "Host"}

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=request.get_json(), headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=request.get_json(), headers=headers)

        return jsonify(response.json()), response.status_code

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
