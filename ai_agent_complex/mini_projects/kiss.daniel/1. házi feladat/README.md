# Groq CLI példa

Ez a mappa egy egyszerű Python CLI szkriptet tartalmaz, amely Groq Chat API-t hív meg a parancssorból vagy stdin-ről beolvasott prompttal.

Fájlok
- `query_openai.py`: A fő script, ami elküldi a promptot a Groq ChatCompletion végpontjára és kiírja a választ.

Követelmények

- Python 3.8+ (vagy újabb)
- Telepítsd a `groq` csomagot:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install groq
```

API kulcs

A script automatikusan betölti a `GROQ_API_KEY` értékét a `mini_projects/kiss.daniel/.env` fájlból. Alternatívaként megadhatod az `--api-key` opcióval is.

Példa `.env` fájl tartalma:

```bash
GROQ_API_KEY=gsk_...
```

Használat

- Parancssori argumentumként megadva a promptot:

```bash
python3 "mini_projects/kiss.daniel/1. házi feladat/query_openai.py" "Mondd el röviden, mi a Python list comprehension"
```

- Pipe-olt stdin például:

```bash
echo "Írj egy rövid motivációs idézetet" | python3 "mini_projects/kiss.daniel/1. házi feladat/query_openai.py"
```

- Megadható `--api-key`, `--model` és `--system` opció is:

```bash
python3 "mini_projects/kiss.daniel/1. házi feladat/query_openai.py" --model llama-3.3-70b-versatile --system "You are a helpful assistant." "Hogyan írjunk unit tesztet Pythonban?"
```

Megjegyzések
- A script a Groq Python könyvtárat használja (`groq.Groq()` client).
- Elérhető modellek: `llama-3.3-70b-versatile`, `llama-3.1-70b-versatile`, `mixtral-8x7b-32768`, stb.
- Ha szeretnéd, hozzáadhatok egy `requirements.txt`-et vagy egy egyszerű `Makefile`/`run.sh` futtatókört.

További lépések
- Futtassuk a scriptet és ellenőrizzük, hogy működik-e a te OpenAI kulcsoddal. Szeretnéd, hogy futtassam (helyileg) vagy csak a fájlokat készítsem elő? 
