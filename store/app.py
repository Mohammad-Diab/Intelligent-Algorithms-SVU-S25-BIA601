from flask import Flask, render_template

import db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-change-me"
    db.init_app(app)

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
