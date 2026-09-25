with open('.env', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('YOUR_CONTRACT_ADDRESS', '0x2169C854f514516038A068cCF758C2b8D40bCe01')

with open('.env', 'w', encoding='utf-8') as f:
    f.write(text)
