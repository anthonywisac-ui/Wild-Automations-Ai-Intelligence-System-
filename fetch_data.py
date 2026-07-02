import json, httpx, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://uooxhovwovsvsaoqbsmv.supabase.co/rest/v1/bot_alerts'
key = 'sb_secret_ZaM-fwCAMWLBepEM-SyGVw_cKMz3X6w'
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
}
with httpx.Client(verify=False) as client:
    r = client.get(url, headers=headers, params={'select': '*', 'order': 'created_at.desc', 'limit': '200'})
    data = r.json()
    if isinstance(data, list):
        with open('data_dump.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'TOTAL: {len(data)} rows saved to data_dump.json')
    else:
        print(repr(data))
