import os, requests
r = requests.get(
    "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001",
    params={"year": 2025, "quarter": 1, "city": "11201", "priceClassification": "01"},
    headers={"Ocp-Apim-Subscription-Key": os.environ["REINFOLIB_API_KEY"]}, timeout=60)
print("HTTP", r.status_code)
print(str(r.json())[:600])
