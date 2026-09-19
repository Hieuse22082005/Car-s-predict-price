import codecs

with codecs.open('main.py', 'r', 'utf-8') as f:
    text = f.read()

text = text.replace('from routers import auth, fines, transactions, chat # I', 'from routers import auth, fines, transactions, chat, cars # I')
text = text.replace('app.include_router(chat.router, prefix="/api", tags=["Chat AI"])', 'app.include_router(chat.router, prefix="/api", tags=["Chat AI"])\napp.include_router(cars.router, prefix="/api/v1/cars", tags=["Cars"])')

with codecs.open('main.py', 'w', 'utf-8') as f:
    f.write(text)
