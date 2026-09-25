with open('routers/transactions.py', 'r', encoding='utf-8') as f:
    text = f.read()
    start = text.find('/evaluate/confirm')
    end = text.find('@router.get("/stats")')
with open('temp_confirm.txt', 'w', encoding='utf-8') as f:
    f.write(text[start-20:end])
