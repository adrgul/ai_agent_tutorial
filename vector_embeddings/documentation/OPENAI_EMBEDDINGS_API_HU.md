# OpenAI Embeddings REST API - Teljes Fejlesztői Útmutató

https://platform.openai.com/docs/guides/embeddings

## Tartalomjegyzék
- [Áttekintés](#áttekintés)
- [Hitelesítés](#hitelesítés)
- [API Végpont](#api-végpont)
- [Kérés Formátum](#kérés-formátum)
- [Kérés Paraméterei](#kérés-paraméterei)
- [Válasz Formátum](#válasz-formátum)
- [Hibakezelés](#hibakezelés)
- [Kód Példák](#kód-példák)
- [Legjobb Gyakorlatok](#legjobb-gyakorlatok)
- [Sebességkorlátok és Árazás](#sebességkorlátok-és-árazás)
- [Elérhető Modellek](#elérhető-modellek)

---

## Áttekintés

Az OpenAI Embeddings API szöveget numerikus vektor reprezentációkká (embedding-ekké) alakít, amelyek megragadják a szemantikai jelentést. Ezek az embedding-ek hasznosak:

- **Szemantikus keresés** - Hasonló szövegek keresése jelentés alapján
- **Klaszterezés** - Kapcsolódó tartalmak csoportosítása
- **Ajánlások** - Hasonló elemek javaslása
- **Anomália detektálás** - Kiugró értékek azonosítása
- **Osztályozás** - Szövegek kategorizálása

**Alap URL**: `https://api.openai.com/v1`

---

## Hitelesítés

Az OpenAI API minden kérése hitelesítést igényel API kulcs segítségével.

### HTTP Header
```
Authorization: Bearer YOUR_API_KEY
```

### API Kulcs Megszerzése
1. Regisztrálj a [platform.openai.com](https://platform.openai.com) oldalon
2. Navigálj az API Keys szekcióhoz
3. Hozz létre egy új titkos kulcsot
4. Tárold biztonságosan (később nem lesz újra megjelenítve)

⚠️ **Biztonság**: Soha ne tedd közzé az API kulcsodat kliens oldali kódban vagy nyilvános repository-kban.

---

## API Végpont

### Embeddings Végpont
```
POST https://api.openai.com/v1/embeddings
```

---

## Kérés Formátum

### HTTP Header-ök
| Header | Érték | Kötelező |
|--------|-------|----------|
| `Content-Type` | `application/json` | Igen |
| `Authorization` | `Bearer YOUR_API_KEY` | Igen |
| `OpenAI-Organization` | Szervezet azonosítód | Nem |

### Kérés Body
A kérés body-nak egy JSON objektumnak kell lennie a következő struktúrával:

```json
{
  "input": "A beágyazandó szöveg",
  "model": "text-embedding-3-small",
  "encoding_format": "float",
  "dimensions": 1536,
  "user": "user-123"
}
```

---

## Kérés Paraméterei

### Kötelező Paraméterek

#### `input` (string vagy tömb)
Az a szöveg, amelyhez embedding-et szeretnénk generálni.

- **Típus**: `string` vagy `string tömb`
- **Kötelező**: Igen
- **Maximum tokenek**: 8191 token a legtöbb modellnél
- **Példák**:
  ```json
  "input": "A gyors barna róka átugrik a lusta kutya fölött"
  ```
  ```json
  "input": ["Első szöveg", "Második szöveg", "Harmadik szöveg"]
  ```

**Megjegyzések**:
- Több input esetén átadhatsz egy string tömböt
- Minden input külön beágyazásra kerül
- A batch kérések hatékonyabbak, mint az egyedi kérések
- Üres stringek hibát eredményeznek

#### `model` (string)
A használandó embedding modell.

- **Típus**: `string`
- **Kötelező**: Igen
- **Elérhető modellek**:
  - `text-embedding-3-small` - Legújabb, hatékony modell (alapértelmezetten 1536 dimenzió)
  - `text-embedding-3-large` - Legújabb, legképesebb modell (alapértelmezetten 3072 dimenzió)
  - `text-embedding-ada-002` - Régebbi modell (1536 dimenzió)

**Példa**:
```json
"model": "text-embedding-3-small"
```

**Modell választás**:
- **text-embedding-3-small**: Legjobb a legtöbb felhasználási esethez, költséghatékony
- **text-embedding-3-large**: Magasabb pontosság, jobb komplex feladatokhoz
- **text-embedding-ada-002**: Régebbi kompatibilitás

---

### Opcionális Paraméterek

#### `encoding_format` (string)
A visszaadott embedding vektorok formátuma.

- **Típus**: `string`
- **Kötelező**: Nem
- **Alapértelmezett**: `float`
- **Lehetőségek**:
  - `float` - Standard lebegőpontos számok (alapértelmezett)
  - `base64` - Base64 kódolt formátum (kompaktabb átvitelhez)

**Példa**:
```json
"encoding_format": "float"
```

**Mikor használjuk**:
- Használj `float`-ot standard alkalmazásokhoz (könnyebb kezelni)
- Használj `base64`-et, amikor a sávszélesség minimalizálása kritikus

#### `dimensions` (egész szám)
A kimeneti embedding-ek dimenzióinak száma.

- **Típus**: `integer`
- **Kötelező**: Nem
- **Alapértelmezett**: Modellfüggő (1536 a 3-small-nál, 3072 a 3-large-nál)
- **Érvényes tartomány**: Modellfüggő
- **Csak támogatott**: `text-embedding-3-small` és `text-embedding-3-large`

**Példa**:
```json
"dimensions": 512
```

**Felhasználási esetek**:
- Csökkentsd a tárolási és számítási költségeket kevesebb dimenzió használatával
- Kompromisszum: Kevesebb dimenzió = kevesebb szemantikai információ megőrzése
- Hasznos, amikor a tárhely/memória korlátozott
- Minimum ajánlott: 256 dimenzió

**Megjegyzés**: Nem minden modell támogatja az egyedi dimenziókat. A régebbi modellek fix dimenzionalitással rendelkeznek.

#### `user` (string)
A kérést indító végfelhasználó egyedi azonosítója.

- **Típus**: `string`
- **Kötelező**: Nem
- **Maximum hossz**: Nincs meghatározva
- **Cél**: Segít az OpenAI-nak észlelni és megelőzni a visszaéléseket

**Példa**:
```json
"user": "user-12345"
```

**Legjobb gyakorlatok**:
- Használj anonimizált felhasználói azonosítókat
- Ne tartalmazzon személyazonosításra alkalmas információkat
- Hasznos a monitorozáshoz és felhasználónkénti sebességkorlátozáshoz

---

## Válasz Formátum

### Sikeres Válasz

**HTTP Státusz**: `200 OK`

**Válasz Body**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [
        0.0023064255,
        -0.009327292,
        -0.0028842222,
        ...
      ]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 8,
    "total_tokens": 8
  }
}
```

### Válasz Mezők

#### `object` (string)
A visszaadott objektum típusa. Embedding-eknél mindig `"list"`.

#### `data` (tömb)
Embedding objektumok tömbje, minden inputhoz egy.

**Minden embedding objektum tartalmazza**:
- `object` (string): Mindig `"embedding"`
- `index` (integer): Pozíció az input tömbben (0-tól indexelve)
- `embedding` (tömb): Az embedding vektor float-ok tömbjeként

#### `model` (string)
Az embedding-ek generálásához használt modell.

#### `usage` (objektum)
Token használati statisztikák:
- `prompt_tokens` (integer): Tokenek száma az inputban
- `total_tokens` (integer): Összes felhasznált token (embedding-eknél azonos a prompt_tokens-szel)

### Példa Több Inputtal

**Kérés**:
```json
{
  "input": ["Helló világ", "Viszlát világ"],
  "model": "text-embedding-3-small"
}
```

**Válasz**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.002, -0.009, ...]
    },
    {
      "object": "embedding",
      "index": 1,
      "embedding": [0.001, -0.007, ...]
    }
  ],
  "model": "text-embedding-3-small",
  "usage": {
    "prompt_tokens": 6,
    "total_tokens": 6
  }
}
```

---

## Hibakezelés

### Gyakori HTTP Státusz Kódok

| Státusz Kód | Jelentés | Gyakori Okok |
|-------------|---------|---------------|
| `400 Bad Request` | Érvénytelen kérés | Hibás formátumú JSON, érvénytelen paraméterek |
| `401 Unauthorized` | Hitelesítés sikertelen | Érvénytelen vagy hiányzó API kulcs |
| `403 Forbidden` | Hozzáférés megtagadva | Nem megfelelő jogosultságok |
| `429 Too Many Requests` | Sebességkorlát túllépve | Túl sok kérés az időablakban |
| `500 Internal Server Error` | Szerver hiba | Átmeneti OpenAI szolgáltatás probléma |
| `503 Service Unavailable` | Szolgáltatás túlterhelt | Nagy forgalom, próbálkozz újra visszalépéssel |

### Hiba Válasz Formátum

```json
{
  "error": {
    "message": "Invalid API key provided",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  }
}
```

### Hiba Típusok

- `invalid_request_error` - Probléma a kérés formátumával vagy paramétereivel
- `authentication_error` - Érvénytelen API kulcs
- `permission_error` - Nem megfelelő jogosultságok
- `rate_limit_error` - Túl sok kérés
- `server_error` - OpenAI szerver probléma

### Hibakezelés Kódban

```python
import requests
import time

def get_embedding_with_retry(text, api_key, max_retries=3):
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
            elif response.status_code == 429:
                # Sebességkorlát - exponenciális visszalépés
                wait_time = 2 ** attempt
                print(f"Sebességkorlát. Várakozás {wait_time}s...")
                time.sleep(wait_time)
            elif response.status_code >= 500:
                # Szerver hiba - újrapróbálkozás
                print(f"Szerver hiba. Újrapróbálkozás... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                # Kliens hiba - ne próbáld újra
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            print(f"Kérés sikertelen: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
    
    raise Exception("Maximális újrapróbálkozások száma túllépve")
```

---

## Kód Példák

### Python `requests` használatával

```python
import requests

def get_embedding(text, api_key, model="text-embedding-3-small"):
    """Embedding beszerzése nyers HTTP kéréssel."""
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "input": text,
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    return data["data"][0]["embedding"]

# Használat
api_key = "sk-..."
embedding = get_embedding("Helló, világ!", api_key)
print(f"Embedding dimenzió: {len(embedding)}")
```

### JavaScript (Node.js)

```javascript
async function getEmbedding(text, apiKey, model = "text-embedding-3-small") {
    const url = "https://api.openai.com/v1/embeddings";
    
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${apiKey}`
        },
        body: JSON.stringify({
            input: text,
            model: model
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP hiba! státusz: ${response.status}`);
    }
    
    const data = await response.json();
    return data.data[0].embedding;
}

// Használat
const apiKey = "sk-...";
const embedding = await getEmbedding("Helló, világ!", apiKey);
console.log(`Embedding dimenzió: ${embedding.length}`);
```

### cURL

```bash
curl https://api.openai.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "input": "A szöveged itt",
    "model": "text-embedding-3-small"
  }'
```

### Batch Feldolgozás

```python
def get_embeddings_batch(texts, api_key, model="text-embedding-3-small"):
    """Embedding-ek beszerzése több szöveghez egy kérésben."""
    url = "https://api.openai.com/v1/embeddings"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "input": texts,  # String-ek tömbje
        "model": model
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    # Rendezés index szerint a sorrend megtartásához
    embeddings = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in embeddings]

# Használat
texts = ["Első szöveg", "Második szöveg", "Harmadik szöveg"]
embeddings = get_embeddings_batch(texts, api_key)
```

---

## Legjobb Gyakorlatok

### 1. Batch Kérések
- Ágyazz be több szöveget egy API hívásban (legfeljebb 2048 input)
- Csökkenti a késleltetést és a költségeket
- Hatékonyabb, mint az egyedi kérések

### 2. Gyorsítótárazás
- Cache-eld az embedding-eket a redundáns API hívások elkerüléséhez
- Az embedding-ek ugyanarra a szövegre és modellre determinisztikusak
- Tárold az embedding-eket adatbázisban vagy fájlrendszerben

### 3. Szöveg Előfeldolgozás
- Távolítsd el a felesleges szóközöket
- Normalizáld a szöveget (kisbetűs, speciális karakterek eltávolítása) ha szükséges
- Vágd le vagy darabold fel a hosszú szövegeket a token limitek betartásához

### 4. Hibakezelés
- Implementálj exponenciális visszalépést sebességkorlátoknál
- Próbálkozz újra átmeneti szerver hibáknál (5xx)
- Ne próbálkozz újra kliens hibáknál (4xx)

### 5. Token Kezelés
- Figyeld a token használatot a válaszokban
- Légy tisztában a modellfüggő token limitekkel
- Használj tokenizer könyvtárakat a költségek becslésére API hívások előtt

### 6. Modell Választás
- Kezd a `text-embedding-3-small`-lal prototípusokhoz
- Frissíts `text-embedding-3-large`-ra, ha a pontosság kritikus
- Fontold meg az egyedi dimenziókat a költségek csökkentéséhez

### 7. Biztonság
- Soha ne tedd közzé az API kulcsokat kliens oldali kódban
- Használj környezeti változókat a kulcsokhoz
- Forgasd rendszeresen a kulcsokat
- Állíts be használati limiteket az OpenAI dashboardon

---

## Sebességkorlátok és Árazás

### Sebességkorlátok (2025. December szerint)

A sebességkorlátok a szervezeti szinttől függően változnak. Példa korlátok:

| Szint | Kérés/perc | Token/perc |
|------|--------------|------------|
| Ingyenes | 3 | 150,000 |
| 1. Szint | 500 | 1,000,000 |
| 2. Szint | 5,000 | 5,000,000 |
| 3+ Szint | Magasabb | Magasabb |

**Megjegyzés**: Ellenőrizd az aktuális limitjeidet a [platform.openai.com/account/limits](https://platform.openai.com/account/limits) oldalon.

### Árazás (1M token-enkénti)

| Modell | Ár |
|-------|-------|
| text-embedding-3-small | $0.02 |
| text-embedding-3-large | $0.13 |
| text-embedding-ada-002 | $0.10 |

**Költség számítás**:
```
Költség = (Tokenek száma / 1,000,000) × Ár 1M token-enként
```

**Példa**:
- 100,000 token `text-embedding-3-small`-lal
- Költség: (100,000 / 1,000,000) × $0.02 = $0.002

---

## Elérhető Modellek

### text-embedding-3-small
- **Dimenziók**: 1536 (alapértelmezett, testreszabható)
- **Teljesítmény**: Erős teljesítmény a legtöbb felhasználási esethez
- **Költség**: $0.02 / 1M token
- **Legjobb**: Általános célú embedding-ek, költségérzékeny alkalmazások

### text-embedding-3-large
- **Dimenziók**: 3072 (alapértelmezett, testreszabható)
- **Teljesítmény**: Legmagasabb minőségű embedding-ek
- **Költség**: $0.13 / 1M token
- **Legjobb**: Nagy pontosságú követelmények, komplex szemantikus feladatok

### text-embedding-ada-002 (Régebbi)
- **Dimenziók**: 1536 (fix)
- **Teljesítmény**: Jó, de a v3 modellek felülmúlják
- **Költség**: $0.10 / 1M token
- **Legjobb**: Régebbi kompatibilitás

### Modell Összehasonlítás

| Jellemző | 3-small | 3-large | ada-002 |
|---------|---------|---------|---------|
| Max tokenek | 8191 | 8191 | 8191 |
| Dimenziók | 1536 (egyedi) | 3072 (egyedi) | 1536 (fix) |
| Egyedi dimenziók | ✅ | ✅ | ❌ |
| Teljesítmény | Jó | Kiváló | Jó |
| Költség | Legalacsonyabb | Legmagasabb | Közepes |

---

## Haladó Témák

### Koszinusz Hasonlóság

Hasonlóság számítás embedding-ek között:

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    """Koszinusz hasonlóság számítása két vektor között."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot_product / (norm1 * norm2)

# Használat
similarity = cosine_similarity(embedding1, embedding2)
# Érték -1 és 1 között (1 = azonos, 0 = ortogonális, -1 = ellentétes)
```

### Dimenzionalitás Csökkentés

```python
# Csökkentett dimenziók kérése
payload = {
    "input": "A szöveged",
    "model": "text-embedding-3-small",
    "dimensions": 512  # Csökkentve az alapértelmezett 1536-ról
}

# Kisebb tárhely, gyorsabb számítás, kissé alacsonyabb pontosság
```

### Hosszú Szövegek Darabolása

```python
def chunk_text(text, max_tokens=8000):
    """Hosszú szöveg darabolása részekre."""
    # Egyszerű szó-alapú darabolás (használj tiktoken-t pontos token számoláshoz)
    words = text.split()
    chunks = []
    current_chunk = []
    current_count = 0
    
    for word in words:
        word_tokens = len(word) // 4 + 1  # Durva becslés
        if current_count + word_tokens > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_count = word_tokens
        else:
            current_chunk.append(word)
            current_count += word_tokens
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks
```

---

## Hibaelhárítás

### Gyakori Problémák

**Probléma**: "Invalid API key"
- **Megoldás**: Ellenőrizd, hogy az API kulcs helyes és aktív
- Nézd meg, nincs-e felesleges szóköz vagy idézőjel

**Probléma**: "Rate limit exceeded"
- **Megoldás**: Implementálj exponenciális visszalépést
- Frissítsd a szervezeti szintet ha szükséges

**Probléma**: "This model's maximum context length is 8191 tokens"
- **Megoldás**: Darabold fel a hosszú szövegeket beágyazás előtt
- Használj token számlálót a hossz ellenőrzéséhez

**Probléma**: Az embedding-ek véletlenszerűnek vagy következetlennek tűnnek
- **Megoldás**: Az embedding-ek determinisztikusak ugyanarra az inputra
- Ellenőrizd, nem hasonlítasz-e össze különböző modellekből származó embedding-eket

**Probléma**: Magas késleltetés
- **Megoldás**: Használj batch kéréseket több szöveghez
- Fontold meg a földrajzi közelséget az API szerverekhez

---

## További Források

- **Hivatalos Dokumentáció**: [platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)
- **API Referencia**: [platform.openai.com/docs/api-reference/embeddings](https://platform.openai.com/docs/api-reference/embeddings)
- **Közösségi Fórum**: [community.openai.com](https://community.openai.com)
- **Státusz Oldal**: [status.openai.com](https://status.openai.com)

---

## Verzió Történet

- **v3 (2024)**: A text-embedding-3-small és text-embedding-3-large bevezetése egyedi dimenziókkal
- **v2 (2022)**: A text-embedding-ada-002 lett a standard
- **v1 (2021)**: Kezdeti embedding modellek

---

*Utolsó Frissítés: 2025. December*
