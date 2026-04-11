import re
from pathlib import Path

src = Path("transactions_inserts.sql")
out = Path("tmp_replay_transactions.sql")
text = src.read_text(encoding="utf-8")
rows = re.findall(r"INSERT INTO transactions VALUES \((.*?)\);", text, flags=re.DOTALL)

sql_lines = ["BEGIN;"]
count = 0
for row in rows:
    parts = [p.strip().strip("'").strip('"') for p in row.split(',')]
    if len(parts) < 11:
        continue
    txn_id = parts[0]
    from_acc = parts[3] or "ACC-UNKNOWN-FROM"
    to_acc = parts[4] or "ACC-UNKNOWN-TO"
    cust_id = parts[5] or f"CUST-{from_acc}"
    amount = parts[6] or "0"
    channel = (parts[8] or "IMPS").upper()
    ts = parts[10] or "2024-01-01 00:00:00"
    dev = f"sha256:dev-{txn_id.lower()}"
    ip = f"sha256:ip-{txn_id.lower()}"
    sql_lines.append(
        "INSERT INTO public.transactions (txn_id, from_account, to_account, amount, channel, \"timestamp\", customer_id, device_fingerprint, ip_address, location) "
        f"VALUES ('{txn_id}', '{from_acc}', '{to_acc}', {amount}, '{channel}', '{ts}+00', '{cust_id}', '{dev}', '{ip}', jsonb_build_object('lat', 19.0760, 'lon', 72.8777)) "
        "ON CONFLICT (txn_id) DO NOTHING;"
    )
    count += 1
sql_lines.append("COMMIT;")
out.write_text("\n".join(sql_lines), encoding="utf-8")
print(count)
