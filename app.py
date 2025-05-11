from config import app, db
import routes
from routes import routes_bp

# Register the Blueprint
app.register_blueprint(routes_bp)

if __name__ == "__main__":
    app.run(debug=True)