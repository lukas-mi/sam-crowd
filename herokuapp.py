import os
import psiturk.experiment_server as exp

psiturk_username = os.environ['PSITURK_USERNAME']
psiturk_password = os.environ['PSITURK_PASSWORD']
psiturk_secret_key = os.environ['SECRET_KEY']

with open('config.txt', 'r+') as f:
    content = f.read()\
        .replace('$PSITURK_USERNAME', psiturk_username)\
        .replace('$PSITURK_PASSWORD', psiturk_username)\
        .replace('$SECRET_KEY', psiturk_secret_key)
    f.seek(0)
    f.write(content)
    f.truncate()

exp.launch()
