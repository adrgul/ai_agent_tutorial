# OpenAI API - Teljes Magyar Útmutató

## Tartalomjegyzék
- [Áttekintés](#áttekintés)
- [Hitelesítés és Alapok](#hitelesítés-és-alapok)
- [Chat Completions API](#chat-completions-api)
- [Elérhető Modellek](#elérhető-modellek)
- [Üzenet Típusok](#üzenet-típusok)
- [Paraméterek Részletes Leírása](#paraméterek-részletes-leírása)
- [Embeddings API](#embeddings-api)
- [Images API](#images-api)
- [Audio API](#audio-api)
- [Moderations API](#moderations-api)
- [Hibakezelés](#hibakezelés)
- [Legjobb Gyakorlatok](#legjobb-gyakorlatok)
- [Árazás és Limitek](#árazás-és-limitek)

---

## Áttekintés

Az OpenAI API hozzáférést biztosít a legmodernebb mesterséges intelligencia modellekhez különböző feladatok elvégzésére:

- **Szöveg generálás** - Chat, szövegkiegészítés, tartalomírás
- **Kód generálás** - Programozási segítség, kód magyarázat
- **Képgenerálás** - DALL-E modellekkel
- **Beszéd** - Szövegből beszéd és beszédfelismerés
- **Embedding-ek** - Szemantikus keresés és hasonlóság
- **Moderáció** - Tartalom szűrés és biztonság

**Alap URL**: `https://api.openai.com/v1`

---

## Hitelesítés és Alapok

### API Kulcs Megszerzése

1. Regisztrálj a [platform.openai.com](https://platform.openai.com) oldalon
2. Navigálj az **API Keys** szekcióhoz
3. Hozz létre egy új secret key-t
4. Másold ki és tárold biztonságosan (később nem látható újra)

### Hitelesítés

Minden API kérés tartalmazza a következő header-t:

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Python Példa

```python
import requests

api_key = "sk-..."
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

---

## Chat Completions API

A Chat Completions API a fő interfész a ChatGPT-szerű beszélgetési AI-hoz.

### Végpont

```
POST https://api.openai.com/v1/chat/completions
```

### Alapvető Példa

```python
import requests

def chat_completion(messages, api_key, model="gpt-4o-mini"):
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()["choices"][0]["message"]["content"]

# Használat
messages = [
    {"role": "system", "content": "Te egy hasznos asszisztens vagy."},
    {"role": "user", "content": "Mi a Python?"}
]

response = chat_completion(messages, api_key)
print(response)
```

### Válasz Formátum

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "A Python egy magas szintű programozási nyelv..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 17,
    "total_tokens": 30
  }
}
```

---

## Elérhető Modellek

### GPT-4o Család (Legújabb, 2024)

#### **gpt-4o** (Flagship)
- **Leírás**: Multimodális (szöveg + kép), leggyorsabb és legokosabb
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 16,384 token
- **Tudás**: 2023 október
- **Ár (input)**: $2.50 / 1M token
- **Ár (output)**: $10.00 / 1M token
- **Legjobb**: Komplex feladatok, multimodális alkalmazások

#### **gpt-4o-mini**
- **Leírás**: Kisebb, gyorsabb, költséghatékonyabb verzió
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 16,384 token
- **Tudás**: 2023 október
- **Ár (input)**: $0.15 / 1M token
- **Ár (output)**: $0.60 / 1M token
- **Legjobb**: Mindennapi feladatok, nagy volumen, költségérzékeny projektek

### GPT-4 Turbo Család

#### **gpt-4-turbo**
- **Leírás**: Legújabb GPT-4 Turbo verzió, JSON mode-dal
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 4,096 token
- **Tudás**: 2023 december
- **Ár (input)**: $10.00 / 1M token
- **Ár (output)**: $30.00 / 1M token
- **Legjobb**: Komplex reasoning, kód generálás

#### **gpt-4-turbo-preview**
- **Leírás**: Preview verzió, gyakran frissül
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 4,096 token
- **Tudás**: 2023 december

### Klasszikus GPT-4

#### **gpt-4**
- **Leírás**: Eredeti GPT-4, kiváló minőség
- **Kontextus ablak**: 8,192 token
- **Kimenet maximum**: 8,192 token
- **Tudás**: 2021 szeptember
- **Ár (input)**: $30.00 / 1M token
- **Ár (output)**: $60.00 / 1M token

#### **gpt-4-32k**
- **Leírás**: Nagy kontextus ablakkal
- **Kontextus ablak**: 32,768 token
- **Kimenet maximum**: 32,768 token
- **Ár (input)**: $60.00 / 1M token
- **Ár (output)**: $120.00 / 1M token
- **Legjobb**: Hosszú dokumentumok elemzése

### GPT-3.5 Turbo

#### **gpt-3.5-turbo**
- **Leírás**: Gyors, költséghatékony, általános célú
- **Kontextus ablak**: 16,385 token
- **Kimenet maximum**: 4,096 token
- **Tudás**: 2021 szeptember
- **Ár (input)**: $0.50 / 1M token
- **Ár (output)**: $1.50 / 1M token
- **Legjobb**: Egyszerű feladatok, prototípusok, chatbotok

### O1 Család (Reasoning Modellek)

#### **o1-preview**
- **Leírás**: Fejlett reasoning képességekkel
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 32,768 token
- **Ár (input)**: $15.00 / 1M token
- **Ár (output)**: $60.00 / 1M token
- **Legjobb**: Komplex problémamegoldás, tudományos elemzés

#### **o1-mini**
- **Leírás**: Költséghatékony reasoning modell
- **Kontextus ablak**: 128,000 token
- **Kimenet maximum**: 65,536 token
- **Ár (input)**: $3.00 / 1M token
- **Ár (output)**: $12.00 / 1M token
- **Legjobb**: STEM területek, matematika, kódolás

### Modell Összehasonlítás

| Modell | Kontextus | Sebesség | Költség | Intelligencia | Ajánlott Használat |
|--------|-----------|----------|---------|---------------|-------------------|
| gpt-4o | 128K | Nagyon gyors | Közepes | Kiváló | Multimodális, általános |
| gpt-4o-mini | 128K | Nagyon gyors | Alacsony | Jó | Költségérzékeny, nagy volumen |
| gpt-4-turbo | 128K | Gyors | Magas | Kiváló | Komplex feladatok |
| gpt-4 | 8K | Közepes | Nagyon magas | Kiváló | Legacy, speciális |
| gpt-3.5-turbo | 16K | Nagyon gyors | Nagyon alacsony | Jó | Egyszerű chatbotok |
| o1-preview | 128K | Lassabb | Magas | Reasoning | Komplex problémák |
| o1-mini | 128K | Lassabb | Közepes | Reasoning | STEM, kód |

---

## Üzenet Típusok

A Chat Completions API üzeneteket használ a beszélgetés felépítéséhez. Minden üzenet tartalmaz egy **role** (szerepkör) és **content** (tartalom) mezőt.

### 1. System Üzenet

**Szerepkör**: `"system"`  
**Cél**: A modell viselkedésének és személyiségének beállítása

```json
{
  "role": "system",
  "content": "Te egy barátságos és segítőkész Python programozási asszisztens vagy. Mindig adj példakódokat a válaszaidban."
}
```

**Jellemzők**:
- Általában a beszélgetés elején szerepel
- Beállítja a modell "személyiségét"
- Nem kötelező, de erősen ajánlott
- Lehet több is (ritkább)

**Példák**:
```python
# Szakmai asszisztens
{"role": "system", "content": "Te egy szakértő jogtanácsadó vagy."}

# Kreatív író
{"role": "system", "content": "Te egy kreatív sci-fi történetíró vagy."}

# Humor
{"role": "system", "content": "Válaszolj vicces és humoros módon."}

# Tömörség
{"role": "system", "content": "Adj rövid, tömör válaszokat, maximum 2 mondatban."}
```

### 2. User Üzenet

**Szerepkör**: `"user"`  
**Cél**: A felhasználó kérdése vagy utasítása

```json
{
  "role": "user",
  "content": "Hogyan használjak dictionary-t Pythonban?"
}
```

**Jellemzők**:
- A felhasználó inputját reprezentálja
- Lehet kérdés, utasítás, vagy bármilyen kérés
- Általában váltakozik az assistant üzenetekkel
- Lehet több is egy beszélgetésben

**Példák**:
```python
# Egyszerű kérdés
{"role": "user", "content": "Mi a főváros Franciaország?"}

# Kód kérés
{"role": "user", "content": "Írj egy függvényt, ami megfordít egy stringet."}

# Komplex utasítás
{"role": "user", "content": "Elemezd ezt a szöveget és találd meg a fő témákat."}

# Multimodális (kép + szöveg)
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Mi van ezen a képen?"},
    {"type": "image_url", "image_url": {"url": "https://..."}}
  ]
}
```

### 3. Assistant Üzenet

**Szerepkör**: `"assistant"`  
**Cél**: A modell válasza vagy korábbi válaszok (beszélgetési történet)

```json
{
  "role": "assistant",
  "content": "Pythonban a dictionary egy kulcs-érték párokból álló adatszerkezet. Például: my_dict = {'név': 'János', 'kor': 30}"
}
```

**Jellemzők**:
- A modell által generált válaszok
- Használható a beszélgetési kontextus fenntartására
- Few-shot learning-hez is használható

**Példák beszélgetésben**:
```python
messages = [
    {"role": "system", "content": "Te egy Python tanár vagy."},
    {"role": "user", "content": "Mi a változó?"},
    {"role": "assistant", "content": "A változó egy névvel ellátott tároló hely a memóriában."},
    {"role": "user", "content": "Adj példát!"}
]
```

**Few-shot learning**:
```python
messages = [
    {"role": "system", "content": "Fordíts angolról magyarra."},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Helló"},
    {"role": "user", "content": "Thank you"},
    {"role": "assistant", "content": "Köszönöm"},
    {"role": "user", "content": "Good morning"}
]
```

### 4. Tool/Function Üzenetek

**Szerepkör**: `"tool"` vagy `"function"`  
**Cél**: Function calling eredményeinek visszaadása

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 22, \"condition\": \"sunny\"}"
}
```

**Használat Function Calling-gal**:
```python
# 1. Modell meghív egy függvényt
messages = [
    {"role": "user", "content": "Mi az időjárás Budapesten?"}
]

# Modell válasza tool_call-al
# 2. Mi végrehajtjuk a függvényt
weather_data = get_weather("Budapest")

# 3. Visszaadjuk az eredményt
messages.append({
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": json.dumps(weather_data)
})

# 4. Modell végső válasza
```

### Multimodális Üzenetek (Kép + Szöveg)

**Támogatott modellek**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4-vision

```python
# Kép URL-ről
message = {
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "Mit látsz ezen a képen?"
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "https://example.com/image.jpg"
            }
        }
    ]
}

# Kép base64 kódolással
import base64

with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Elemezd ezt a képet"},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_data}"
            }
        }
    ]
}
```

### Üzenet Strukturálás - Legjobb Gyakorlatok

#### 1. Egyszerű Beszélgetés
```python
messages = [
    {"role": "system", "content": "Te egy segítőkész asszisztens vagy."},
    {"role": "user", "content": "Szia!"},
    {"role": "assistant", "content": "Szia! Miben segíthetek?"},
    {"role": "user", "content": "Mesélj a Python-ról"}
]
```

#### 2. Kontextus Fenntartása
```python
# Tárolj minden üzenetet
conversation_history = [
    {"role": "system", "content": "Te egy személyi asszisztens vagy."}
]

# Felhasználói input
conversation_history.append({"role": "user", "content": "Emlékezz, John vagyok"})

# API válasz
response = chat_completion(conversation_history, api_key)
conversation_history.append({"role": "assistant", "content": response})

# Következő kérdés
conversation_history.append({"role": "user", "content": "Mi a nevem?"})
# Modell emlékezni fog: "John"
```

#### 3. Token Limit Kezelése
```python
def trim_history(messages, max_tokens=4000):
    """Tartsd a beszélgetést a token limiten belül."""
    # Mindig tartsd meg a system üzenetet
    system_msg = [msg for msg in messages if msg["role"] == "system"]
    other_msgs = [msg for msg in messages if msg["role"] != "system"]
    
    # Csak az utolsó N üzenetet tartsd meg
    return system_msg + other_msgs[-10:]  # Utolsó 10 üzenet
```

---

## Paraméterek Részletes Leírása

### Kötelező Paraméterek

#### **model** (string)
Az használandó AI modell neve.

```json
"model": "gpt-4o-mini"
```

**Opciók**: Lásd [Elérhető Modellek](#elérhető-modellek) szekciót

#### **messages** (array)
A beszélgetés üzeneteinek tömbje.

```json
"messages": [
  {"role": "system", "content": "..."},
  {"role": "user", "content": "..."}
]
```

---

### Opcionális Paraméterek

#### **temperature** (number, 0-2)
Vezérli a véletlenszerűséget a válaszokban.

- **Tartomány**: 0.0 - 2.0
- **Alapértelmezett**: 1.0
- **Alacsonyabb értékek** (0.0-0.3): Determinisztikus, konzisztens, pontos
- **Közepes értékek** (0.7-1.0): Kiegyensúlyozott
- **Magasabb értékek** (1.5-2.0): Kreatív, változatos, kiszámíthatatlan

```python
# Precíz válaszok (pl. matematika)
"temperature": 0.0

# Általános beszélgetés
"temperature": 0.7

# Kreatív írás
"temperature": 1.5
```

**Példa**:
```python
# Matematikai kérdés
payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Mennyi 2+2?"}],
    "temperature": 0.0  # Mindig ugyanaz a válasz: "4"
}

# Történet írás
payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Írj egy rövid sci-fi történetet"}],
    "temperature": 1.5  # Változatos, kreatív történetek
}
```

#### **max_tokens** (integer)
A generált válasz maximum token száma.

- **Alapértelmezett**: A modell maximuma vagy végtelen
- **Minimum**: 1
- **Maximum**: Modellfüggő (pl. 4096, 16384, stb.)

```python
"max_tokens": 500  # Maximum 500 token a válaszban
```

**Megjegyzés**: A `prompt_tokens + max_tokens` nem haladhatja meg a modell kontextus ablakát.

**Használat**:
```python
# Rövid válaszok
"max_tokens": 50

# Hosszú dokumentumok
"max_tokens": 4000

# Költség kontroll
"max_tokens": 100  # Limitáld a költségeket
```

#### **top_p** (number, 0-1)
Nucleus sampling - alternatíva a temperature-höz.

- **Tartomány**: 0.0 - 1.0
- **Alapértelmezett**: 1.0
- **Működés**: Csak a top P valószínűségű tokeneket veszi figyelembe

```python
"top_p": 0.9  # A top 90% valószínűségű tokenek közül választ
```

**Ajánlás**: Vagy a `temperature`-t vagy a `top_p`-t változtasd, ne mindkettőt.

#### **n** (integer)
Hány választ generáljon a modell.

- **Alapértelmezett**: 1
- **Használat**: Több alternatíva közül választáshoz

```python
"n": 3  # 3 különböző válasz
```

**Válasz több választással**:
```json
{
  "choices": [
    {"index": 0, "message": {"content": "Első válasz..."}},
    {"index": 1, "message": {"content": "Második válasz..."}},
    {"index": 2, "message": {"content": "Harmadik válasz..."}}
  ]
}
```

**Költség**: Minden generált válasz után fizetsz!

#### **stream** (boolean)
Streamelés engedélyezése (válaszok darabokban érkeznek).

- **Alapértelmezett**: false
- **Használat**: Valós idejű felhasználói élményhez

```python
"stream": true
```

**Példa streamelésre**:
```python
import requests
import json

def stream_chat(messages, api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "stream": True
    }
    
    response = requests.post(url, headers=headers, json=payload, stream=True)
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str == '[DONE]':
                    break
                data = json.loads(data_str)
                if 'choices' in data:
                    delta = data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        print(content, end='', flush=True)
```

#### **stop** (string vagy array)
Megállító szekvenciák, ahol a generálás leáll.

```python
"stop": "\n"  # Megáll új sornál

"stop": ["END", "###"]  # Megáll ezeknek valamelyikénél
```

**Példa**:
```python
# Lista generálás korlátozott elemekkel
payload = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Adj 3 programozási nyelvet"}],
    "stop": "4."  # Megáll a 4. elemnél
}
```

#### **presence_penalty** (number, -2.0 - 2.0)
Csökkenti az ismétlődés valószínűségét a már említett témákban.

- **Tartomány**: -2.0 - 2.0
- **Alapértelmezett**: 0
- **Pozitív értékek**: Ösztönzi az új témákat
- **Negatív értékek**: Ösztönzi a témák ismétlését

```python
"presence_penalty": 0.6  # Változatosabb témák
```

#### **frequency_penalty** (number, -2.0 - 2.0)
Csökkenti az ismétlődő szavak valószínűségét.

- **Tartomány**: -2.0 - 2.0
- **Alapértelmezett**: 0
- **Pozitív értékek**: Ösztönzi a változatosságot
- **Negatív értékek**: Engedi az ismétléseket

```python
"frequency_penalty": 0.5  # Kevesebb szóismétlés
```

**Különbség**:
- `presence_penalty`: Témák/koncepciók szintjén
- `frequency_penalty`: Szó szintjén

#### **logit_bias** (object)
Befolyásolja bizonyos tokenek valószínűségét.

```python
"logit_bias": {
  "1234": 100,  # Token 1234 nagyon valószínű
  "5678": -100  # Token 5678 lehetetlen
}
```

**Használat**: Speciális esetekre (pl. tiltott szavak kizárása)

#### **user** (string)
Végfelhasználó azonosítója (visszaélés monitorozáshoz).

```python
"user": "user-12345"
```

#### **response_format** (object)
Kimenet formátumának meghatározása.

```python
# JSON kimenet
"response_format": {"type": "json_object"}
```

**Támogatott modellek**: gpt-4o, gpt-4-turbo

**Példa JSON kimenettel**:
```python
messages = [
    {"role": "system", "content": "Válaszolj JSON formátumban."},
    {"role": "user", "content": "Adj 3 gyümölcsöt név és szín tulajdonsággal."}
]

payload = {
    "model": "gpt-4o-mini",
    "messages": messages,
    "response_format": {"type": "json_object"}
}

# Válasz:
# {
#   "fruits": [
#     {"name": "alma", "color": "piros"},
#     {"name": "banán", "color": "sárga"},
#     {"name": "szőlő", "color": "lila"}
#   ]
# }
```

#### **seed** (integer)
Determinisztikus kimenethez (béta funkció).

```python
"seed": 42
```

**Használat**: Reprodukálható eredményekhez (tesztelés, debugging)

#### **tools** / **functions**
Function calling definíciók (lásd Function Calling szekciót).

---

### Teljes Példa Sok Paraméterrel

```python
import requests

def advanced_chat(api_key):
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Te egy kreatív történetíró vagy."
            },
            {
                "role": "user",
                "content": "Írj egy rövid sci-fi történetet robotokról."
            }
        ],
        "temperature": 1.2,           # Kreatív
        "max_tokens": 500,            # Rövid történet
        "top_p": 0.95,                # Változatosság
        "frequency_penalty": 0.5,     # Kevesebb ismétlés
        "presence_penalty": 0.3,      # Új témák
        "n": 2,                       # 2 változat
        "stop": ["THE END"],          # Megáll itt
        "user": "user-12345"          # Felhasználó azonosító
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    # Mindkét történet változat
    for i, choice in enumerate(data["choices"]):
        print(f"\n=== Történet {i+1} ===")
        print(choice["message"]["content"])
    
    # Token használat
    print(f"\nToken használat: {data['usage']}")
    
    return data

# Használat
response = advanced_chat("sk-...")
```

---

## Embeddings API

Lásd a részletes [OPENAI_EMBEDDINGS_API_HU.md](OPENAI_EMBEDDINGS_API_HU.md) dokumentációt.

### Gyors Áttekintés

```python
def get_embedding(text, api_key):
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()["data"][0]["embedding"]
```

**Modellek**:
- `text-embedding-3-small` - $0.02 / 1M token
- `text-embedding-3-large` - $0.13 / 1M token
- `text-embedding-ada-002` - $0.10 / 1M token (régebbi)

---

## Images API

Képgenerálás DALL-E modellekkel.

### Végpont

```
POST https://api.openai.com/v1/images/generations
```

### Képgenerálás

```python
def generate_image(prompt, api_key, size="1024x1024"):
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "size": size,
        "quality": "standard",
        "n": 1
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    return response.json()["data"][0]["url"]

# Használat
image_url = generate_image(
    "Egy futurisztikus város éjszaka, neon fényekkel",
    api_key
)
print(f"Kép URL: {image_url}")
```

### Paraméterek

- **model**: `dall-e-2` vagy `dall-e-3`
- **prompt**: Kép leírása (max 4000 karakter)
- **size**: 
  - DALL-E 3: `1024x1024`, `1792x1024`, `1024x1792`
  - DALL-E 2: `256x256`, `512x512`, `1024x1024`
- **quality**: `standard` vagy `hd` (csak DALL-E 3)
- **style**: `vivid` vagy `natural` (csak DALL-E 3)
- **n**: Hány képet generáljon (1-10, DALL-E 2-nél)

### Árazás

**DALL-E 3**:
- Standard 1024×1024: $0.040 / kép
- Standard 1024×1792, 1792×1024: $0.080 / kép
- HD 1024×1024: $0.080 / kép
- HD 1024×1792, 1792×1024: $0.120 / kép

**DALL-E 2**:
- 1024×1024: $0.020 / kép
- 512×512: $0.018 / kép
- 256×256: $0.016 / kép

---

## Audio API

### Text-to-Speech (TTS)

Szövegből beszéd generálás.

```python
def text_to_speech(text, api_key, voice="alloy"):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Mentés fájlba
    with open("speech.mp3", "wb") as f:
        f.write(response.content)
    
    return "speech.mp3"

# Használat
text_to_speech("Helló, ez egy teszt.", api_key, voice="nova")
```

**Modellek**:
- `tts-1`: Gyorsabb, alacsonyabb minőség ($15.00 / 1M karakter)
- `tts-1-hd`: Magasabb minőség ($30.00 / 1M karakter)

**Hangok**: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

### Speech-to-Text (Whisper)

Beszédfelismerés.

```python
def transcribe_audio(audio_file_path, api_key):
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    with open(audio_file_path, "rb") as audio_file:
        files = {"file": audio_file}
        data = {"model": "whisper-1"}
        
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
    
    return response.json()["text"]

# Használat
text = transcribe_audio("audio.mp3", api_key)
print(f"Átirat: {text}")
```

**Támogatott formátumok**: mp3, mp4, mpeg, mpga, m4a, wav, webm  
**Max fájlméret**: 25 MB  
**Ár**: $0.006 / perc

---

## Moderations API

Tartalom moderálás és szűrés.

```python
def moderate_content(text, api_key):
    url = "https://api.openai.com/v1/moderations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()["results"][0]
    return result

# Használat
text = "Ez egy tesztszöveg moderálásra."
result = moderate_content(text, api_key)

print(f"Flagged: {result['flagged']}")
print(f"Kategóriák: {result['categories']}")
print(f"Kategória pontszámok: {result['category_scores']}")
```

**Kategóriák**:
- `hate`: Gyűlöletkeltés
- `hate/threatening`: Fenyegető gyűlölet
- `self-harm`: Öncsonkítás
- `sexual`: Szexuális tartalom
- `sexual/minors`: Kiskorúakkal kapcsolatos szexuális tartalom
- `violence`: Erőszak
- `violence/graphic`: Grafikus erőszak

**Ár**: INGYENES

---

## Hibakezelés

### HTTP Státusz Kódok

| Kód | Jelentés | Megoldás |
|-----|----------|----------|
| 200 | Sikeres | - |
| 400 | Rossz kérés | Ellenőrizd a paramétert |
| 401 | Hitelesítési hiba | Ellenőrizd az API kulcsot |
| 403 | Hozzáférés megtagadva | Nincs jogosultság |
| 404 | Nem található | Rossz endpoint |
| 429 | Túl sok kérés | Rate limiting, várj |
| 500 | Szerver hiba | Próbáld újra később |
| 503 | Szolgáltatás nem elérhető | Túlterhelt, várakozz |

### Hibakezelési Minta

```python
import requests
import time

def api_call_with_retry(url, headers, payload, max_retries=3):
    """API hívás újrapróbálkozással."""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate limit
                retry_after = int(response.headers.get('Retry-After', 2 ** attempt))
                print(f"Rate limited. Várakozás {retry_after}s...")
                time.sleep(retry_after)
                
            elif response.status_code >= 500:
                # Szerver hiba
                wait_time = 2 ** attempt
                print(f"Szerver hiba. Várakozás {wait_time}s...")
                time.sleep(wait_time)
                
            else:
                # Kliens hiba - ne próbáld újra
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            print(f"Timeout ({attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise
                
        except requests.exceptions.RequestException as e:
            print(f"Hálózati hiba: {e}")
            if attempt == max_retries - 1:
                raise
    
    raise Exception("Max újrapróbálkozások száma elérve")
```

---

## Legjobb Gyakorlatok

### 1. API Kulcs Biztonság
```python
# ✅ HELYES - Környezeti változó
import os
api_key = os.getenv("OPENAI_API_KEY")

# ❌ HELYTELEN - Hard-coded
api_key = "sk-..."  # NE ÍRD BE A KÓDBA!
```

### 2. Token Kezelés
```python
# Token számolás (hozzávetőleges)
def estimate_tokens(text):
    """Durva token becslés."""
    return len(text) // 4

# Költség becslés
def estimate_cost(prompt, completion, model="gpt-4o-mini"):
    prices = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00}
    }
    
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion)
    
    price = prices[model]
    cost = (prompt_tokens * price["input"] + 
            completion_tokens * price["output"]) / 1_000_000
    
    return cost
```

### 3. Streaming Válasz
```python
# Jobb felhasználói élmény hosszú válaszoknál
payload["stream"] = True
```

### 4. Prompt Engineering
```python
# Jó prompt struktúra
prompt = """
# Feladat
Írj egy Python függvényt.

# Követelmények
- Dokumentáció docstring-gel
- Type hinting-ek
- Error handling

# Példa kimenet
def my_function(param: str) -> int:
    '''Leírás'''
    pass
"""
```

### 5. Költségoptimalizálás
```python
# Használj olcsóbb modellt egyszerű feladatokhoz
model = "gpt-3.5-turbo"  # $0.50/1M helyett

# Limitáld a max_tokens-t
max_tokens = 500  # Ne generáljon feleslegesen sokat

# Cache-elj válaszokat
cache = {}
if prompt in cache:
    return cache[prompt]
```

---

## Árazás és Limitek

### Árazás Összefoglaló (2025 December)

| Modell | Input (1M token) | Output (1M token) |
|--------|------------------|-------------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-4 | $30.00 | $60.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| o1-preview | $15.00 | $60.00 |
| o1-mini | $3.00 | $12.00 |

### Rate Limitek

Szintenként változó. Példa (Tier 1):
- **Kérések**: 500 / perc
- **Tokenek**: 1,000,000 / perc

Ellenőrizd: [platform.openai.com/account/limits](https://platform.openai.com/account/limits)

---

## További Források

- **OpenAI Platform**: [platform.openai.com](https://platform.openai.com)
- **API Dokumentáció**: [platform.openai.com/docs](https://platform.openai.com/docs)
- **API Referencia**: [platform.openai.com/docs/api-reference](https://platform.openai.com/docs/api-reference)
- **Közösség**: [community.openai.com](https://community.openai.com)
- **Cookbook**: [cookbook.openai.com](https://cookbook.openai.com)

---

*Utolsó Frissítés: 2025. December 10.*
