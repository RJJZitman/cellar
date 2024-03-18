from api.main import app
from api.ApiSwaggerModifier import ApiModifier

swagger_hook = ApiModifier(app=app)
swagger_hook.save_openapi(
    path="docs/assets/",
    title="VinoDB API",
    version="0.1.0",
    hosts=["http://127.0.0.1:8000", "invalid"],
    descriptions=[
        "This host is used for local development.",
        "invalid host for testing purposes.",
    ],
)
