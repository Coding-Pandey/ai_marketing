from fastapi import FastAPI
from Seo_process.seo_routes import router as seo_router
from Ppc_process.ppc_routes import router as ppc_router
from social_media.social_media_routes import router as social_media_router
from content_generation.content_generation_routes import router as content_generate_router
from S3_bucket.bucket_routes import router as bucket_router

app = FastAPI(title="AI marketing app",
    description="",
    version="1.0.0",
    root_path="/api"
         )

@app.get("/")
def read_root():
    return {"message": "welcome to Ai marketing"}

# SEO routes app.include_router(seo_router, prefix="/seo", tags=["SEO"])
app.include_router(seo_router)
# ppc routes
app.include_router(ppc_router)
# social media post routes
app.include_router(social_media_router)
# s3 bucket routes
app.include_router(bucket_router)
# content generation
app.include_router(content_generate_router)


