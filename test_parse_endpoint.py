"""Quick smoke test for POST /parse/statement"""
import urllib.request
import json

boundary = "----FormBoundary7MA4YWxkTrZu0gW"
csv_path = r"d:\Code\ML\25IOH08\generated_statements\raju_sbi_statement.csv"

with open(csv_path, "rb") as f:
    csv_data = f.read()

parts = []
for name, value in [("borrower_name", "Raju"), ("employment_type", "self_employed"),
                     ("gst_applicable", "false"), ("loan_amount_requested", "120000")]:
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())

parts.append(
    f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"raju_sbi_statement.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode()
    + csv_data
    + b"\r\n"
)
parts.append(f"--{boundary}--\r\n".encode())
body = b"".join(parts)

req = urllib.request.Request(
    "http://127.0.0.1:8099/parse/statement",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST",
)
r = urllib.request.urlopen(req)
data = json.loads(r.read())
print("Status:", r.status)
print("Bank:", data["detected_bank"])
print("Confidence:", data["confidence_score"])
print("Months:", data["statement_months"])
print("Warnings:", data.get("parser_warnings", []))
for k, v in data["parsed_signals"].items():
    print(f"  {k}: {v}")
