from marcapp import app
from werkzeug.contrib.fixers import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == '__main__':
    app.debug = True
    app.run()
