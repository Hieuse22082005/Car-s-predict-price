import re
with open('routers/transactions.py', 'r', encoding='utf-8') as f:
    text = f.read()
    endpoints = re.findall(r'@router\.\w+\(\"([^\"]+)\"', text)
    print('\n'.join(endpoints))
