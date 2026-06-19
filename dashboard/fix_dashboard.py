# ============================================================
# fix_dashboard.py — Monitor de Email Infratech Engenharia
# ============================================================
# Gera o data.json lido pelo index.html
# Roda a cada 2 minutos via crontab:
#   */2 * * * * /root/gera_dashboard_data.sh
#
# Para rodar manualmente:
#   python3 /root/fix_dashboard.py
#
# Output: /var/www/dashboard/data.json
# ============================================================

# TODO: Aba de fila com emails presos e detalhes
# TODO: Log de emails rejeitados/bloqueados
# TODO: Log de bounces (falha na entrega)
# TODO: Log de tentativas de login falhas
# ============================================================

import re, json, subprocess, email
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

BRT = timezone(timedelta(hours=-3))

def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.stdout.decode('utf-8', errors='replace')

def brt_from_log(ts_str):
    try:
        ts_str = ts_str[:19].replace('T',' ')
        t = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        return t.astimezone(BRT).strftime('%d/%m/%Y'), t.astimezone(BRT).strftime('%H:%M:%S')
    except:
        return '', ''

def decode_hdr(raw):
    try:
        # Normaliza headers dobrados (continuation lines com espaço/tab)
        raw = re.sub(r'\r?\n[ \t]+', ' ', raw.strip())
        parts = email.header.decode_header(raw)
        result = ''
        for p, enc in parts:
            if isinstance(p, bytes):
                result += p.decode(enc or 'utf-8', errors='replace')
            else:
                result += p
        return result.strip()[:120]
    except:
        return raw.strip()[:120] if raw else ''

usuarios = [u.strip() for u in run(['docker','exec','poste','ls','/data/domains/infratechengenharia.com/']).strip().split('\n') if u.strip()]

recebidos = []
hoje_brt = datetime.now(BRT)
dois_dias_atras = hoje_brt - timedelta(days=2)

for user in usuarios:
    for pasta in ['cur', 'new']:
        path = f'/data/domains/infratechengenharia.com/{user}/Maildir/{pasta}/'
        ls_out = run(['docker','exec','poste','ls','-t', path])
        if not ls_out.strip():
            continue
        arquivos = [a.strip() for a in ls_out.strip().split('\n') if a.strip()][:15]
        for arq in arquivos:
            filepath = path + arq
            content = run(['docker','exec','poste','head','-120', filepath])
            if not content:
                continue

            from_h    = re.search(r'^From:\s*(.+)',            content, re.MULTILINE)
            to_h      = re.search(r'^To:\s*(.+)',              content, re.MULTILINE)
            cc_h      = re.search(r'^Cc:\s*(.+)',              content, re.MULTILINE)
            subj_h    = re.search(r'^Subject:\s*(.+)',         content, re.MULTILINE)
            date_h    = re.search(r'^Date:\s*(.+)',            content, re.MULTILINE)
            msgid_h   = re.search(r'^Message-ID:\s*<([^>]+)>', content, re.MULTILINE)
            reply_h   = re.search(r'^In-Reply-To:',            content, re.MULTILINE)
            fwd_h     = re.search(r'Subject:.*?(Fwd|Fw:|Enc:|Encaminhado)', content, re.MULTILINE | re.IGNORECASE)

            # Spam
            spam_flag_h  = re.search(r'^X-Spam-Flag:\s*(.+)',            content, re.MULTILINE | re.IGNORECASE)
            spam_score_h = re.search(r'^X-Spam-Score:\s*([\d\.\-]+)',    content, re.MULTILINE | re.IGNORECASE)
            spam_status_h= re.search(r'^X-Spam-Status:\s*(.+)',          content, re.MULTILINE | re.IGNORECASE)

            # DKIM / SPF / DMARC
            auth_h = re.search(r'^Authentication-Results:\s*(.+)', content, re.MULTILINE | re.IGNORECASE)

            # Anexo
            has_attach = bool(re.search(r'filename\s*=\s*["\']?(.+?)["\']?\s*[\r\n;]', content, re.IGNORECASE))

            subj = decode_hdr(subj_h.group(1)) if subj_h else ''

            # --- Filtro de data: emails sem data ou com data inválida são descartados ---
            if not date_h:
                continue
            data_futura = False
            try:
                t = parsedate_to_datetime(date_h.group(1).strip())
                t_brt = t.astimezone(BRT)
                if t_brt.replace(tzinfo=None) < dois_dias_atras.replace(tzinfo=None):
                    continue
                # Data mais de 1 dia no futuro = header forjado (técnica de spam)
                if t_brt.replace(tzinfo=None) > (hoje_brt + timedelta(days=1)).replace(tzinfo=None):
                    data_futura = True
                data = t_brt.strftime('%d/%m/%Y')
                hora = t_brt.strftime('%H:%M:%S')
            except:
                continue  # data ilegível → descarta

            # Spam detection
            is_spam = False
            if spam_flag_h and 'yes' in spam_flag_h.group(1).lower():
                is_spam = True
            elif spam_status_h and spam_status_h.group(1).lower().startswith('yes'):
                is_spam = True
            spam_score = spam_score_h.group(1) if spam_score_h else ''

            # DKIM / SPF / DMARC
            dkim = spf = dmarc = ''
            if auth_h:
                auth_str = auth_h.group(1)
                m = re.search(r'dkim=(\w+)', auth_str, re.IGNORECASE)
                if m: dkim = m.group(1)
                m = re.search(r'spf=(\w+)', auth_str, re.IGNORECASE)
                if m: spf = m.group(1)
                m = re.search(r'dmarc=(\w+)', auth_str, re.IGNORECASE)
                if m: dmarc = m.group(1)

            if is_spam or data_futura:
                tipo = 'Spam'
            elif reply_h:
                tipo = 'Resposta'
            elif fwd_h:
                tipo = 'Reencaminhado'
            else:
                tipo = 'Normal'

            recebidos.append({
                "data": data,
                "hora": hora,
                "destinatario": f'{user}@infratechengenharia.com',
                "remetente": decode_hdr(from_h.group(1)) if from_h else '',
                "para": decode_hdr(to_h.group(1)) if to_h else '',
                "cc": decode_hdr(cc_h.group(1)) if cc_h else '',
                "assunto": subj,
                "tipo": tipo,
                "spam_score": spam_score,
                "anexo": has_attach,
                "dkim": dkim,
                "spf": spf,
                "dmarc": dmarc,
                "msgid": msgid_h.group(1)[:60] if msgid_h else '',
                "pasta": "INBOX"
            })

recebidos.sort(key=lambda x: (x['data'], x['hora']), reverse=True)
recebidos = recebidos[:300]

# Lê o log completo para correlacionar sender/rcpt pelo UUID do Haraka
UUID_RE = re.compile(r'\[([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12})\]', re.IGNORECASE)
full_log = run(['docker','exec','poste','tail','-n','20000','/data/log/s6/haraka-submission/current'])
all_lines = full_log.strip().split('\n')

uuid_from = {}
uuid_rcpt = {}
for line in all_lines:
    uuid_m = UUID_RE.search(line)
    if not uuid_m:
        continue
    uid = uuid_m.group(1).upper()
    from_m = re.search(r'C: MAIL FROM:\s*<?([^>\s]+@[^>\s]+)>?', line, re.IGNORECASE)
    if from_m:
        uuid_from[uid] = from_m.group(1).strip('<>')
    rcpt_m = re.search(r'C: RCPT TO:\s*<?([^>\s]+@[^>\s]+)>?', line, re.IGNORECASE)
    if rcpt_m:
        uuid_rcpt[uid] = rcpt_m.group(1).strip('<>')

lines2 = [l for l in all_lines if 'delivered' in l.lower() and 'domain=' in l and 'domain=infratechengenharia.com' not in l][-200:]

enviados = []
for line in lines2:
    ts     = re.search(r'^([\d-]+ [\d:\.]+)', line)
    domain = re.search(r'domain=(\S+)', line)
    host   = re.search(r'host=(\S+)', line)
    rcpts  = re.search(r'rcpts=(\S+)', line)
    uuid_m = UUID_RE.search(line)
    uid    = uuid_m.group(1).upper() if uuid_m else ''
    if ts and domain:
        data, hora = brt_from_log(ts.group(1)[:19])
        enviados.append({
            "data": data, "hora": hora,
            "dominio_destino": domain.group(1),
            "host": host.group(1) if host else "",
            "rcpts": rcpts.group(1) if rcpts else "",
            "remetente": uuid_from.get(uid, ''),
            "destinatario": uuid_rcpt.get(uid, '')
        })

enviados = list(reversed(enviados))
hoje = hoje_brt.strftime('%d/%m/%Y')
rec_hoje = sum(1 for r in recebidos if r['data'] == hoje)
env_hoje = sum(1 for e in enviados if e['data'] == hoje)

ip = run(['docker','exec','poste','redis-cli','-s','/var/run/redis/redis.sock','KEYS','guard|*']).strip()
fila_out = run(['docker','exec','poste','find','/data/queue','-type','f']).strip()
fila = len([l for l in fila_out.split('\n') if l])

data_out = {
    "atualizado": hoje_brt.strftime('%d/%m/%Y %H:%M:%S'),
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
