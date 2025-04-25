from fastapi import FastAPI
from Seo_process.seo_routes import router as seo_router
from Ppc_process.ppc_routes import router as ppc_router
from social_media.social_media_routes import router as social_media_router
from content_generation.content_generation_routes import router as content_generate_router
from S3_bucket.bucket_routes import router as bucket_router
from auth.users import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="AI marketing app",
    description="",
    version="1.0.0",
    root_path="/api"
         )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key="!secret"
)

@app.get("/")
def read_root():
    return {"message": "welcome to Ai marketing"}

app.include_router(auth_router, tags=["Auth"])
# SEO routes app.include_router(seo_router, prefix="/seo", tags=["SEO"])
app.include_router(seo_router, tags=["SEO"])
# ppc routes
app.include_router(ppc_router, tags=["PPC"])
# social media post routes
app.include_router(social_media_router, tags=["Social Media"])
# s3 bucket routes
app.include_router(bucket_router, tags=["S3 Bucket"])
# content generation
app.include_router(content_generate_router, tags=["Content Generation"])


