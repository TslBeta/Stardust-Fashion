import os

import pymysql
from flask import Flask, jsonify, request

from stardust.common import ApiError
from stardust.db import close_db, one


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.json.ensure_ascii = False
    app.teardown_appcontext(close_db)

    from stardust.auth import bp as auth_bp
    from stardust.catalog import bp as catalog_bp
    from stardust.commerce import bp as commerce_bp
    from stardust.momo import bp as momo_bp

    for blueprint in (auth_bp, catalog_bp, commerce_bp, momo_bp):
        app.register_blueprint(blueprint)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/v1/health")
    def health():
        one("SELECT 1 AS ok")
        return jsonify({"status": "ok", "database": "mysql"})

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status

    @app.errorhandler(pymysql.err.OperationalError)
    def database_error(error):
        app.logger.error("MySQL connection failed: %s", error.args[0] if error.args else "unknown")
        return jsonify({"error": {"code": "DATABASE_UNAVAILABLE", "message": "Không kết nối được MySQL. Kiểm tra dịch vụ và .env."}}), 503

    @app.errorhandler(404)
    def missing(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": {"code": "NOT_FOUND", "message": "API không tồn tại."}}), 404
        return app.send_static_file("index.html")

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unexpected server error")
        return jsonify({"error": {"code": "SERVER_ERROR", "message": "Máy chủ gặp lỗi. Xem log terminal."}}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT", "5000")), debug=False, threaded=True)
