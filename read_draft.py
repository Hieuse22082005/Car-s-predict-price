with open('routers/transactions.py', 'r', encoding='utf-8') as f:
    text = f.read()
    start = text.find('/evaluate/draft')
    end = text.find('/evaluate/confirm')
with open('temp_draft.txt', 'w', encoding='utf-8') as f:
    f.write(text[start-20:end])
