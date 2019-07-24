import os

from flask import Flask
from flask_bootstrap import Bootstrap

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config = True)
    Bootstrap(app)
    app.config.from_mapping(
        SECRET_KEY = 'dev' ,
        DATABASE = os.path.join(app.instance_path, 'flask.sqlite'),
        )
    if test_config == None:
        app.config.from_pyfile('config.py', silent = True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)

    except OSError:
        pass

    @app.route('/hello')
    def hello():
        return 'Hello World'

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')

    '''Will Workflow'''

    from . import manual_workflow
    app.register_blueprint(manual_workflow.bp)

    from . import model_workflow
    app.register_blueprint(model_workflow.bp)

    from . import view_workflow
    app.register_blueprint(view_workflow.bp)

    
    from . import upload_workflow
    app.register_blueprint(upload_workflow.bp)

       
    from . import rebuild_workflow
    app.register_blueprint(rebuild_workflow.bp)



    
    
    return app

