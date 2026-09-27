import os
from anthropic import Anthropic

c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
for m in c.models.list():
    print(m.id)
