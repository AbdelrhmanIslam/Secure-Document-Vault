import os

from authlib.integrations.flask_client import OAuth

oauth = OAuth()
REGISTERED_PROVIDERS = set()

def init_oauth(app):
    REGISTERED_PROVIDERS.clear()
    oauth.init_app(app)
    if app.config['AUTHLIB_INSECURE_TRANSPORT']:
        os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'

    if app.config['OAUTH_GITHUB_CLIENT_ID'] and app.config['OAUTH_GITHUB_CLIENT_SECRET']:
        oauth.register(
            name='github',
            client_id=app.config['OAUTH_GITHUB_CLIENT_ID'],
            client_secret=app.config['OAUTH_GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )
        REGISTERED_PROVIDERS.add('github')

    if app.config['OAUTH_GOOGLE_CLIENT_ID'] and app.config['OAUTH_GOOGLE_CLIENT_SECRET']:
        oauth.register(
            name='google',
            client_id=app.config['OAUTH_GOOGLE_CLIENT_ID'],
            client_secret=app.config['OAUTH_GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
        REGISTERED_PROVIDERS.add('google')

def is_provider_configured(provider):
    return provider in REGISTERED_PROVIDERS
