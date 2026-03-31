"""
Wikidata SPARQL source — 100% gratuito, sem API key.
Devolve empresas portuguesas por nicho e cidade a partir do Wikidata.
"""
import json
import urllib.request
import urllib.parse
from typing import Optional

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# Tipos de negócio por nicho → QIDs do Wikidata
NICHO_ENTITIES: dict[str, list[str]] = {
    "restaurante":   ["Q11707"],
    "restaurantes":  ["Q11707"],
    "cafe":          ["Q30022", "Q5503"],
    "cafes":         ["Q30022", "Q5503"],
    "bar":           ["Q929763", "Q159711"],
    "bares":         ["Q929763"],
    "clinica":       ["Q1774898"],
    "clinicas":      ["Q1774898"],
    "dentista":      ["Q27349"],
    "dentistas":     ["Q27349"],
    "farmacia":      ["Q35760"],
    "farmacias":     ["Q35760"],
    "hospital":      ["Q16917"],
    "hospitais":     ["Q16917"],
    "hotel":         ["Q27686"],
    "hoteis":        ["Q27686"],
    "ginasio":       ["Q988108"],
    "ginasios":      ["Q988108"],
    "padaria":       ["Q274177"],
    "padarias":      ["Q274177"],
    "supermercado":  ["Q180389"],
    "supermercados": ["Q180389"],
    "cabeleireiro":  ["Q57609"],
    "cabeleireiros": ["Q57609"],
    "barbearia":     ["Q56348"],
    "barbearias":    ["Q56348"],
    "mecanico":      ["Q656601"],
    "oficina":       ["Q656601"],
    "advogado":      ["Q148554"],
    "advogados":     ["Q148554"],
    "escola":        ["Q3914", "Q9842"],
    "escolas":       ["Q3914", "Q9842"],
    "pousada":       ["Q2860826", "Q27686"],
    "spa":           ["Q483370"],
    "veterinario":   ["Q3932296"],
    "veterinarios":  ["Q3932296"],
    "livraria":      ["Q212805"],
    "livrarias":     ["Q212805"],
}

# Cidades portuguesas → QIDs Wikidata
CITY_QIDS: dict[str, str] = {
    "porto":             "Q36677",
    "lisboa":            "Q597",
    "braga":             "Q128169",
    "coimbra":           "Q47809",
    "aveiro":            "Q155530",
    "faro":              "Q46715",
    "viseu":             "Q158150",
    "leiria":            "Q168543",
    "setubal":           "Q186382",
    "setúbal":           "Q186382",
    "funchal":           "Q14785",
    "vila nova de gaia": "Q202063",
    "almada":            "Q203098",
    "amadora":           "Q204516",
    "loures":            "Q204547",
    "guimaraes":         "Q216284",
    "guimarães":         "Q216284",
    "matosinhos":        "Q200399",
    "cascais":           "Q204515",
    "sintra":            "Q153204",
    "viana do castelo":  "Q2415755",
    "braganca":          "Q262989",
    "bragança":          "Q262989",
    "castelo branco":    "Q46801",
    "evora":             "Q46799",
    "évora":             "Q46799",
    "portalegre":        "Q203097",
    "beja":              "Q46811",
    "santarem":          "Q203099",
    "santarém":          "Q203099",
    "penafiel":          "Q174766",
    "barcelos":          "Q211649",
    "famalicao":         "Q174756",
    "famalicão":         "Q174756",
    "felgueiras":        "Q211631",
    "povoa de varzim":   "Q203126",
    "póvoa de varzim":   "Q203126",
    "gondomar":          "Q203112",
    "maia":              "Q200384",
    "valongo":           "Q200403",
    "paredes":           "Q200406",
    "vila do conde":     "Q203127",
}


def _fetch_sparql(query: str, timeout: int = 15) -> Optional[dict]:
    """Executa uma query SPARQL no endpoint público do Wikidata."""
    params = urllib.parse.urlencode({"query": query, "format": "json"})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "ProspectBraza/1.0 (contact@webraza.com)",
        "Accept": "application/sparql-results+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def scrape_wikidata(nicho: str, localidade: str, max_results: int = 20) -> list:
    """Pesquisa empresas no Wikidata por nicho e cidade."""
    nicho_lower = nicho.lower().strip()
    city_lower  = localidade.lower().strip()

    entities = NICHO_ENTITIES.get(nicho_lower, [])
    if not entities and nicho_lower.endswith("s"):
        entities = NICHO_ENTITIES.get(nicho_lower[:-1], [])
    if not entities:
        return []

    city_qid = CITY_QIDS.get(city_lower)
    entity_values = " ".join(f"wd:{e}" for e in entities)

    if city_qid:
        location_clause = f"""
  {{
    ?item wdt:P131 wd:{city_qid}.
  }} UNION {{
    ?item wdt:P131 ?subregion.
    ?subregion wdt:P131 wd:{city_qid}.
  }}"""
    else:
        location_clause = f"""
  ?item wdt:P131 ?loc.
  ?loc rdfs:label ?locLabel.
  FILTER(CONTAINS(LCASE(STR(?locLabel)), "{city_lower}"))"""

    query = f"""
SELECT DISTINCT ?item ?itemLabel ?phone ?website ?email ?morada ?postal WHERE {{
  VALUES ?type {{ {entity_values} }}
  ?item wdt:P31/wdt:P279* ?type.
  {location_clause}
  OPTIONAL {{ ?item wdt:P1329 ?phone. }}
  OPTIONAL {{ ?item wdt:P856 ?website. }}
  OPTIONAL {{ ?item wdt:P968 ?email. }}
  OPTIONAL {{ ?item wdt:P6375 ?morada. }}
  OPTIONAL {{ ?item wdt:P281 ?postal. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "pt,en". }}
}}
LIMIT {max_results * 4}
"""

    data = _fetch_sparql(query)
    if not data:
        return []

    seen: set = set()
    companies: list = []

    for r in data.get("results", {}).get("bindings", []):
        name = r.get("itemLabel", {}).get("value", "").strip()
        if not name or name.startswith("Q") or len(name) < 2:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        company: dict = {"nome": name, "nicho": nicho, "localidade": localidade, "fonte_raw": "Wikidata"}

        phone = r.get("phone", {}).get("value", "")
        if phone:
            company["telefone"] = phone.replace("+351", "").replace(" ", "")

        website = r.get("website", {}).get("value", "")
        if website:
            company["website"] = website

        email = r.get("email", {}).get("value", "")
        if email:
            company["email"] = email.replace("mailto:", "")

        morada = r.get("morada", {}).get("value", "")
        if morada:
            company["morada"] = morada

        postal = r.get("postal", {}).get("value", "")
        if postal:
            company["codigo_postal"] = postal

        companies.append(company)
        if len(companies) >= max_results:
            break

    return companies
