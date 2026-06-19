import re, json, subprocess, email
from datetime import datetime, timezone, timedelta

BRT = timezone(timedelta(hours=-3))

def brt_from_log(ts_str):
    try:
        ts_str = ts_str[:19].replace('T',' ')
        t = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        t = t.astimezone(BRT)
        return t.strftime('%d/%m/%Y'), t.strftime('%H:%M:%S')
    except:
        return '', ''

def decode_header(raw):
    try:
        parts = email.header.decode_header(raw.strip())
        result = ''
        for p, enc in parts:
            if isinstance(p, bytes):
                result += p.decode(enc or 'utf-8', errors='replace')
            else:
                result += p
        return result[:100]
    except:
        return raw.strip()[:100] if raw else ''

# Listar usuarios
result = subprocess.run(['docker','exec','poste','ls','/data/domains/infratechengenharia.com/'], capture_output=True, text=True)
usuarios = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]

recebidos = []
hoje_brt = datetime.now(BRT)
dois_dias_atras = hoje_brt - timedelta(days=2)

for user in usuarios:
    for pasta in ['cur', 'new']:
        path = f'/data/domains/infratechengenharia.com/{user}/Maildir/{pasta}/'
        ls = subprocess.run(['docker','exec','poste','ls','-t', path], capture_output=True, text=True)
        if ls.returncode != 0:
            continue
        arquivos = [a.strip() for a in ls.stdout.strip().split('\n') if a.strip()][:20]
        for arq in arquivos:
            filepath = path + arq
            cat = subprocess.run(['docker','exec','poste','head','-80', filepath], capture_output=True, text=True)
            if cat.returncode != 0:
                continue
            content = cat.stdout

            from_h = re.search(r'^From:\s*(.+)', content, re.MULTILINE)
            to_h = re.search(r'^To:\s*(.+)', content, re.MULTILINE)
            cc_h = re.search(r'^Cc:\s*(.+)', content, re.MULTILINE)
            subj_h = re.search(r'^Subject:\s*(.+)', content, re.MULTILINE)
            date_h = re.search(r'^Date:\s*(.+)', content, re.MULTILINE)
            msgid_h = re.search(r'^Message-ID:\s*<([^>]+)>', content, re.MULTILINE)
            reply_h = re.search(r'^In-Reply-To:', content, re.MULTILINE)
            fwd_h = re.search(r'Subject:.*?(Fwd|Fw:|Enc:|Encaminhado)', content, re.MULTILINE | re.IGNORECASE)

            subj = decode_header(subj_h.group(1)) if subj_h else ''
            data, hora = '', ''

            if date_h:
                try:
                    from email.utils import parsedate_to_datetime
                    t = parsedate_to_datetime(date_h.group(1).strip())
                    t_brt = t.astimezone(BRT)
                    if t_brt < dois_dias_atras.replace(tzinfo=None).replace(tzinfo=BRT):
                        continue
                    data = t_brt.strftime('%d/%m/%Y')
                    hora = t_brt.strftime('%H:%M:%S')
                except:
                    pass

            tipo = 'Resposta' if reply_h else ('Reencaminhado' if fwd_h else 'Normal')

            recebidos.append({
                "data": data,
                "hora": hora,
                "destinatario": f'{user}@infratechengenharia.com',
                "remetente": decode_header(from_h.group(1)) if from_h else '',
                "para": decode_header(to_h.group(1)) if to_h else '',
                "cc": decode_header(cc_h.group(1)) if cc_h else '',
                "assunto": subj,
                "tipo": tipo,
                "msgid": msgid_h.group(1)[:60] if msgid_h else '',
                "pasta": pasta.upper()
            })

recebidos.sort(key=lambda x: (x['data'], x['hora']), reverse=True)
recebidos = recebidos[:300]

# Emails enviados externos
result2 = subprocess.run(['docker','exec','poste','grep','delivered','/data/log/s6/haraka-submission/current'], capture_output=True, text=True)
lines2 = [l for l in result2.stdout.strip().split('\n') if 'domain=' in l and 'domain=infratechengenharia.com' not in l][-200:]

enviados = []
for line in lines2:
    ts = re.search(r'^([\d-]+ [\d:\.]+)', line)
    domain = re.search(r'domain=(\S+)', line)
    host = re.search(r'host=(\S+)', line)
    rcpts = re.search(r'rcpts=(\S+)', line)
    sender = re.search(r'sender=([^\s]+)', line)
    if ts and domain:
        data, hora = brt_from_log(ts.group(1)[:19])
        enviados.append({
            "data": data,
            "hora": hora,
            "dominio_destino": domain.group(1),
            "host": host.group(1) if host else "",
            "rcpts": rcpts.group(1) if rcpts else "",
            "remetente": sender.group(1) if sender else ""
        })

enviados = list(reversed(enviados))

hoje = datetime.now(BRT).strftime('%d/%m/%Y')
rec_hoje = sum(1 for r in recebidos if r['data'] == hoje)
env_hoje = sum(1 for e in enviados if e['data'] == hoje)

ip = subprocess.run(['docker','exec','poste','redis-cli','-s','/var/run/redis/redis.sock','KEYS','guard|*'], capture_output=True, text=True).stdout.strip()
fila_out = subprocess.run(['docker','exec','poste','find','/data/queue','-type','f'], capture_output=True, text=True).stdout.strip()
fila = len([l for l in fila_out.split('\n') if l])

data_out = {
    "atualizado": datetime.now(BRT).strftime('%d/%m/%Y %H:%M:%S'),
    "recebidos_hoje": rec_hoje,
    "enviados_hoje": env_hoje,
    "ip_bloqueado": ip if ip else "nenhum",
    "fila": fila,
    "recebidos": recebidos,
    "enviados": enviados
}

with open('/var/www/dashboard/data.json', 'w') as f:
    json.dump(data_out, f, indent=2, ensure_ascii=False)

print(f"OK - recebidos: {len(recebidos)}, enviados: {len(enviados)}, hoje: {hoje}")
