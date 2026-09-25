with open('.env', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'ADMIN_PRIVATE_KEY=.*', 'ADMIN_PRIVATE_KEY=947c05c8a890a9d23aaeded0096b3aba9516465ee309f8adb09e5d769d1c4ad5', text)

with open('.env', 'w', encoding='utf-8') as f:
    f.write(text)
