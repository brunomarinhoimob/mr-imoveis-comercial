from utils.supremo_config import TOKEN_SUPREMO
import http.client

conn = http.client.HTTPSConnection("api.supremocrm.com.br")
headers = {
   'Authorization': f'Bearer {TOKEN_SUPREMO}'
}

conn.request("GET", "/v1/leads?pagina=1", headers=headers)
res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
