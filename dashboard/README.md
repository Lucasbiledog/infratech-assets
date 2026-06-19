# Dashboard Monitor de Email — Infratech Engenharia

## Acesso
- URL: http://186.233.225.171:8888
- Servidor: node263339-env-7740545 (Saveincloud)

## Arquivos
- `fix_dashboard.py` — Script Python que lê os logs e gera o data.json
- `index.html` — Frontend do dashboard (HTML/CSS/JS puro)
- `data.json` — Gerado automaticamente pelo script (não editar)

## Como funciona
1. O script `fix_dashboard.py` roda a cada 2 minutos via crontab
2. Ele lê os emails do Maildir de todos os usuários e os logs do Haraka
3. Gera o `/var/www/dashboard/data.json`
4. O `index.html` lê o `data.json` via fetch e exibe na tela

## Deploy após editar
```bash
# No servidor via SSH
curl -s "https://raw.githubusercontent.com/Lucasbiledog/infratech-assets/main/dashboard/fix_dashboard.py" -o /root/fix_dashboard.py
curl -s "https://raw.githubusercontent.com/Lucasbiledog/infratech-assets/main/dashboard/index.html" -o /var/www/dashboard/index.html
python3 /root/fix_dashboard.py
```

## Crontab atual
```
*/15 * * * * /root/monitor_email.sh
*/2  * * * * /root/gera_dashboard_data.sh
```

## Estrutura do data.json
```json
{
  "atualizado": "19/06/2026 10:00:00",
  "recebidos_hoje": 120,
  "enviados_hoje": 4,
  "ip_bloqueado": "nenhum",
  "fila": 1,
  "recebidos": [
    {
      "data": "19/06/2026",
      "hora": "10:05:28",
      "destinatario": "cicera@infratechengenharia.com",
      "remetente": "Infratech Engenharia LTDA <noreply@infratechengenharia.com>",
      "para": "cicera@infratechengenharia.com",
      "cc": "",
      "assunto": "Aviso de Aniversario",
      "tipo": "Normal",
      "msgid": "abc123@infratechengenharia.com",
      "pasta": "INBOX"
    }
  ],
  "enviados": [
    {
      "data": "19/06/2026",
      "hora": "10:05:20",
      "dominio_destino": "gmail.com",
      "host": "gmail-smtp-in.l.google.com",
      "rcpts": "1/0/0",
      "remetente": "lucas@infratechengenharia.com"
    }
  ]
}
```

## Melhorias pendentes (TODO)
- [ ] Mostrar remetente completo nos enviados externos
- [ ] Aba de fila com emails presos e detalhes
- [ ] Filtro por data (campo date picker)
- [ ] Log de emails rejeitados/bloqueados
- [ ] Log de bounces (falha na entrega)
- [ ] Log de tentativas de login falhas
- [ ] Score de spam por email
- [ ] Emails com anexo (nome e tamanho)
- [ ] DKIM/SPF/DMARC resultado por email
