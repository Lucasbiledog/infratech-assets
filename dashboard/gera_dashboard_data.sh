#!/bin/bash

DIR="/var/www/dashboard"
mkdir -p $DIR

DATA_HOJE=$(date '+%Y-%m-%d')
ATUALIZADO=$(date '+%d/%m/%Y %H:%M:%S')

RECEBIDOS_HOJE=$(docker exec poste grep "stored mail" /data/log/mail.log 2>/dev/null | grep "$DATA_HOJE" | wc -l)
ENVIADOS_HOJE=$(docker exec poste grep "delivered" /data/log/s6/haraka-submission/current 2>/dev/null | grep "$DATA_HOJE" | grep "domain=" | grep -v "domain=infratechengenharia.com" | wc -l)
IP_BLOQUEADO=$(docker exec poste redis-cli -s /var/run/redis/redis.sock KEYS "guard|*" 2>/dev/null | head -1)
FILA=$(docker exec poste find /data/queue -type f 2>/dev/null | wc -l)

# Emails recebidos com remetente
docker exec poste grep "stored mail" /data/log/mail.log 2>/dev/null | tail -200 > /tmp/recebidos.txt

# Logs do haraka-smtp para pegar remetentes
docker exec poste grep -E "sender=|MAIL FROM:|stored mail" /data/log/s6/haraka-smtp/current 2>/dev/null | tail -500 > /tmp/smtp_log.txt

python3 << 'PYEOF'
import re, json

# Processar emails recebidos
recebidos = []
with open('/tmp/recebidos.txt') as f:
    for line in f:
        ts = re.search(r'^(\S+)', line)
        dest = re.search(r'lmtp\(([^)]+)\)', line)
        msgid = re.search(r'msgid=<([^>]+)>', line)
        mailbox = re.search(r"mailbox '([^']+)'", line)
        if ts and dest and msgid:
            t = ts.group(1).replace('T', ' ').split('+')[0]
            # Extrair data e hora separados
            parts = t.split(' ')
            data = parts[0] if len(parts) > 0 else ''
            hora = parts[1][:8] if len(parts) > 1 else ''
            msgid_val = msgid.group(1)
            # Tentar extrair dominio remetente do msgid
            remetente_dominio = msgid_val.split('@')[-1] if '@' in msgid_val else ''
            recebidos.append({
                "data": data,
                "hora": hora,
                "destinatario": dest.group(1),
                "remetente_dominio": remetente_dominio,
                "msgid": msgid_val,
                "pasta": mailbox.group(1) if mailbox else "INBOX"
            })

with open('/tmp/recebidos.json', 'w') as f:
    json.dump(recebidos, f)
PYEOF

# Emails enviados externos com remetente
docker exec poste grep "delivered" /data/log/s6/haraka-submission/current 2>/dev/null | grep "domain=" | grep -v "domain=infratechengenharia.com" | tail -200 > /tmp/enviados.txt
docker exec poste grep "sender=" /data/log/s6/haraka-submission/current 2>/dev/null | tail -500 > /tmp/senders.txt

python3 << 'PYEOF'
import re, json

enviados = []
with open('/tmp/enviados.txt') as f:
    for line in f:
        ts = re.search(r'^([\d-]+ [\d:\.]+)', line)
        domain = re.search(r'domain=(\S+)', line)
        host = re.search(r'host=(\S+)', line)
        rcpts = re.search(r'rcpts=(\S+)', line)
        sender = re.search(r'sender=([^\s]+)', line)
        if ts and domain:
            t = ts.group(1)[:19]
            parts = t.split(' ')
            data = parts[0] if len(parts) > 0 else ''
            hora = parts[1][:8] if len(parts) > 1 else ''
            enviados.append({
                "data": data,
                "hora": hora,
                "dominio_destino": domain.group(1),
                "host": host.group(1) if host else "",
                "rcpts": rcpts.group(1) if rcpts else "",
                "remetente": sender.group(1) if sender else ""
            })

with open('/tmp/enviados.json', 'w') as f:
    json.dump(enviados, f)
PYEOF

python3 << PYEOF
import json

with open('/tmp/recebidos.json') as f:
    recebidos = json.load(f)

with open('/tmp/enviados.json') as f:
    enviados = json.load(f)

data = {
    "atualizado": "$ATUALIZADO",
    "recebidos_hoje": $RECEBIDOS_HOJE,
    "enviados_hoje": $ENVIADOS_HOJE,
    "ip_bloqueado": "${IP_BLOQUEADO:-nenhum}",
    "fila": $FILA,
    "recebidos": list(reversed(recebidos)),
    "enviados": list(reversed(enviados))
}

with open('/var/www/dashboard/data.json', 'w') as f:
    json.dump(data, f, indent=2)

print("OK - recebidos:", len(recebidos), "enviados:", len(enviados))
PYEOF
