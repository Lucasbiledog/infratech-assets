
import re, json, subprocess

from datetime import datetime, timezone, timedelta



BRT = timezone(timedelta(hours=-3))



# Emails recebidos

result = subprocess.run(['docker', 'exec', 'poste', 'grep', 'stored mail', '/data/log/mail.log'], capture_output=True, text=True)

lines = result.stdout.strip().split('\n')[-200:]



recebidos = []

for line in lines:

    ts = re.search(r'^(\S+)', line)

    dest = re.search(r'lmtp\(([^)]+)\)', line)

    msgid = re.search(r'msgid=<([^>]+)>', line)

    mailbox = re.search(r"mailbox '([^']+)'", line)

    if ts and dest and msgid:

        try:

            t_str = ts.group(1).replace('+00:00','').replace('T',' ')

            t_utc = datetime.strptime(t_str[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

            t_brt = t_utc.astimezone(BRT)

            data = t_brt.strftime('%d/%m/%Y')

            hora = t_brt.strftime('%H:%M:%S')

        except:

            data = hora = ''

        msgid_val = msgid.group(1)

        remetente = msgid_val.split('@')[-1] if '@' in msgid_val else msgid_val

        recebidos.append({

            "data": data,

            "hora": hora,

            "destinatario": dest.group(1),

            "remetente": remetente,

            "msgid": msgid_val,

            "pasta": mailbox.group(1) if mailbox else "INBOX"

        })



# Emails enviados externos

result2 = subprocess.run(['docker', 'exec', 'poste', 'grep', 'delivered', '/data/log/s6/haraka-submission/current'], capture_output=True, text=True)

lines2 = [l for l in result2.stdout.strip().split('\n') if 'domain=' in l and 'domain=infratechengenharia.com' not in l][-200:]



enviados = []

for line in lines2:

    ts = re.search(r'^([\d-]+ [\d:\.]+)', line)

    domain = re.search(r'domain=(\S+)', line)

    host = re.search(r'host=(\S+)', line)

    rcpts = re.search(r'rcpts=(\S+)', line)

    sender = re.search(r'sender=([^\s]+)', line)

    if ts and domain:

        try:

            t_str = ts.group(1)[:19]

            t_utc = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

            t_brt = t_utc.astimezone(BRT)

            data = t_brt.strftime('%d/%m/%Y')

            hora = t_brt.strftime('%H:%M:%S')

        except:

            data = hora = ''

        enviados.append({

            "data": data,

            "hora": hora,

            "dominio_destino": domain.group(1),

            "host": host.group(1) if host else "",

            "rcpts": rcpts.group(1) if rcpts else "",

            "remetente": sender.group(1) if sender else ""

        })



# Contadores hoje

hoje = datetime.now(BRT).strftime('%d/%m/%Y')

rec_hoje = sum(1 for r in recebidos if r['data'] == hoje)

env_hoje = sum(1 for e in enviados if e['data'] == hoje)



# IP bloqueado

ip = subprocess.run(['docker', 'exec', 'poste', 'redis-cli', '-s', '/var/run/redis/redis.sock', 'KEYS', 'guard|*'], capture_output=True, text=True).stdout.strip()

fila = subprocess.run(['docker', 'exec', 'poste', 'find', '/data/queue', '-type', 'f'], capture_output=True, text=True).stdout.strip().count('\n')



from datetime import datetime as dt

data = {

    "atualizado": dt.now(BRT).strftime('%d/%m/%Y %H:%M:%S'),

    "recebidos_hoje": rec_hoje,

    "enviados_hoje": env_hoje,

    "ip_bloqueado": ip if ip else "nenhum",

    "fila": fila,

    "recebidos": list(reversed(recebidos)),

    "enviados": list(reversed(enviados))

}



with open('/var/www/dashboard/data.json', 'w') as f:

    json.dump(data, f, indent=2)



print(f"OK - recebidos: {len(recebidos)}, enviados: {len(enviados)}, hoje BRT: {hoje}")

