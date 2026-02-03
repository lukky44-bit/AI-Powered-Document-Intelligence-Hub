from fastapi import FastAPI
from app.core.config import settings
from app.routes import register_routes
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limiter import limiter


app = FastAPI(title=settings.PROJECT_NAME)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_routes(app)


@app.get("/")
def root():
    return {"message": "Document AI Hub is running"}
