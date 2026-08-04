from fastapi import FastAPI

app = FastAPI(
    title= "BananaKart API",
    description="The world's most chaotic banana marketplace"
    )

@app.get("/")
def home():
    return {
        "message" : "Welcome to BananaKart"
    }