from flask import Flask, render_template

import db
import auth
import products


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-change-me"
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.before_request(auth.load_logged_in_user)

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
