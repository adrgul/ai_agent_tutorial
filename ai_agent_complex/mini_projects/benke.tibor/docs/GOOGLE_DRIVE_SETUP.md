# Google Drive API Setup

A KnowledgeRouter integrálva van a Google Drive API-val, hogy hozzáférjen megosztott mappákhoz és azok tartalmát használja a marketing domain RAG válaszokhoz.

## Előfeltételek

### 1. Google Cloud Project létrehozása

1. Menj a [Google Cloud Console](https://console.cloud.google.com/)-ra
2. Hozz létre új projektet vagy használj egy meglévőt
3. Engedélyezd a **Google Drive API**-t:
   - Navigation Menu → APIs & Services → Library
   - Keress rá: "Google Drive API"
   - Kattints "Enable"-re

### 2. OAuth 2.0 Credentials létrehozása

1. Navigation Menu → APIs & Services → Credentials
2. Kattints "Create Credentials" → "OAuth client ID"
3. Válaszd ki: **Desktop app** (nem Web application!)
4. Add meg a nevet (pl. "KnowledgeRouter Desktop")
5. Kattints "Create"
6. **Töltsd le a JSON fájlt** (ez lesz a `client_secret.json`)

### 3. Client Secret telepítése

Helyezd el a letöltött `client_secret.json` fájlt:

```bash
backend/credentials/client_secret.json
```

**FONTOS:** Ez a fájl már benne van a `.gitignore`-ban, NEM kerül fel a GitHub-ra!

## Használat

### API Endpoint tesztelése

```bash
# Backend elindítása
docker-compose up

# Fájlok listázása a marketing mappából (böngészőben vagy curl-lel)
curl http://localhost:8001/api/google-drive/files/
```

**Első futtatáskor:**
1. Böngésző ablak nyílik meg
2. Jelentkezz be a Google fiókodba
3. Engedélyezd a hozzáférést
4. A token automatikusan elmentődik: `backend/credentials/token.json`

**Következő futtatásoknál** már nem kell újra bejelentkezni.

### API Paraméterek

```http
GET /api/google-drive/files/

Query parameters:
  - folder_id (optional): Google Drive folder ID
    Default: 1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR (marketing folder)
  
  - mime_type (optional): Filter by MIME type
    Példa: application/pdf, image/jpeg, etc.
```

**Példa válasz:**

```json
{
  "success": true,
  "folder_id": "1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR",
  "file_count": 5,
  "files": [
    {
      "id": "abc123...",
      "name": "Brand Guidelines.pdf",
      "mimeType": "application/pdf",
      "size": "2048576",
      "createdTime": "2025-01-15T10:30:00.000Z",
      "modifiedTime": "2025-01-16T14:20:00.000Z",
      "webViewLink": "https://drive.google.com/file/d/abc123.../view"
    }
  ]
}
```

## Folder ID megtalálása

Google Drive URL-ből:
```
https://drive.google.com/drive/folders/1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR
                                          ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                          Ez a folder ID
```

## Fájlstruktúra

```
backend/
  credentials/              # Git-ről kizárva!
    client_secret.json      # Google Cloud Console-ról letöltve
    token.json              # OAuth után automatikusan létrejön
  infrastructure/
    google_drive_client.py  # Google Drive API wrapper
  api/
    views.py                # API endpoint: GoogleDriveFilesAPIView
```

## Későbbi funkciók (jelenleg fejlesztés alatt)

1. **Fájl tartalom letöltése** - PDF, DOCX, stb. olvasása
2. **RAG integráció** - Marketing dokumentumok indexelése Qdrant-ba
3. **Auto-sync** - Automatikus szinkronizáció Google Drive változásokkal
4. **File upload** - Feltöltés a marketing mappába

## Hibaelhárítás

### "client_secret.json not found"

Ellenőrizd, hogy a fájl a megfelelő helyen van:
```bash
ls backend/credentials/client_secret.json
```

### "Access token expired"

Töröld a `token.json`-t és jelentkezz be újra:
```bash
rm backend/credentials/token.json
# Következő API híváskor újra autentikál
```

### "Insufficient permissions"

Ellenőrizd, hogy a Google Drive mappához van-e hozzáférésed (megosztva veled).

## Biztonsági megjegyzések

⚠️ **SOHA ne commitolj:**
- `client_secret.json`
- `token.json`
- Bármilyen `.json` fájlt a `credentials/` mappából

✅ Ezek már a `.gitignore`-ban vannak:
```
backend/credentials/*.json
```
