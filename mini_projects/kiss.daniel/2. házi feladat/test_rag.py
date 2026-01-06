"""
Test script for RAG application.

This script:
1. Stores 5 sample documents with different content
2. Asks 5 questions via the chat endpoint
3. Displays the results

Prerequisites:
- FastAPI server running on http://localhost:8000
- Ollama running with qwen2.5:14b-instruct model
- Qdrant running on http://localhost:6333
"""

import httpx
import asyncio
import json
from typing import Dict, Any


# Test configuration
BASE_URL = "http://localhost:8000"
TENANT = "test-tenant"
USER_ID = "test-user"

# Sample documents to store
SAMPLE_DOCUMENTS = [
    {
        "document_id": "dok-001",
        "ocr_text": """
        Távmunkavégzési Szabályzat
        
        Cégünk támogatja a rugalmas munkavégzést. A munkavállalók hetente legfeljebb 3 napot 
        dolgozhatnak otthonról. A távmunkavégzési kérelmeket a közvetlen vezetőnek jóvá kell 
        hagynia. Minden távmunkában dolgozó munkavállaló köteles rendszeres kommunikációt 
        fenntartani a Slack csatornákon keresztül, és videókonferencián részt venni minden 
        tervezett csapatértekezleten.
        
        A távmunkához szükséges eszközöket, beleértve a laptopokat és monitorokat, az IT 
        osztály biztosítja. A munkavállalók felelősek a biztonságos otthoni munkakörnyezet 
        kialakításáért és a vállalati biztonsági szabályzatok betartásáért.
        
        A távmunka során minden dolgozónak biztosítania kell a zavartalan internetkapcsolatot 
        és megfelelő munkakörnyezetet. Munkaidő alatt elérhetőnek kell lennie.
        """
    },
    {
        "document_id": "dok-002",
        "ocr_text": """
        Munkavállalói Juttatások Áttekintése
        
        Egészségbiztosítás: Teljes körű egészségügyi, fogászati és szemészeti ellátás a 
        munkavállalók és családtagjaik számára. A biztosítás a munkaviszony első napjától 
        érvényes.
        
        Szabadság: Az új munkavállalók évente 20 nap fizetett szabadságra jogosultak. Ez 
        3 év után 25 napra, 5 év után pedig 30 napra emelkedik.
        
        Nyugdíjprogram: A cég a bruttó fizetés 10%-áig megtéríti az önkéntes nyugdíjpénztári 
        befizetéseket.
        
        Szakmai Fejlődés: Minden munkavállaló évi 500,000 Ft kerettel rendelkezik konferenciák, 
        tanfolyamok és képzések költségeinek fedezésére.
        
        Cafeteria: Évi bruttó 1,200,000 Ft értékű cafeteria juttatás, melyet SZÉP kártyára, 
        önkéntes nyugdíjpénztárba vagy egyéb jogosult célokra lehet fordítani.
        """
    },
    {
        "document_id": "dok-003",
        "ocr_text": """
        IT Biztonsági Irányelvek
        
        Jelszó Követelmények: Minden jelszónak legalább 12 karakter hosszúnak kell lennie, 
        és tartalmaznia kell nagybetűt, kisbetűt, számot és speciális karaktert. A jelszavakat 
        90 naponta kötelező megváltoztatni.
        
        Kétfaktoros Hitelesítés: Minden vállalati rendszer és alkalmazás esetében kötelező 
        a kétfaktoros azonosítás használata.
        
        Adatosztályozás: Minden vállalati adat Nyilvános, Belső, Bizalmas vagy Korlátozott 
        besorolású. A munkavállalóknak az adatokat a besorolási szintjüknek megfelelően kell 
        kezelniük.
        
        Incidens Bejelentés: Minden biztonsági incidenst az észleléstől számított 1 órán 
        belül jelenteni kell az IT Biztonsági osztálynak.
        """
    },
    {
        "document_id": "dok-004",
        "ocr_text": """
        Teljesítményértékelési Folyamat
        
        Éves Értékelések: Minden munkavállaló részt vesz az éves teljesítményértékelésen, 
        melyet decemberben tartanak. Az értékelés magában foglalja az önértékelést, a 
        vezető értékelését és a kollégák visszajelzéseit.
        
        Célkitűzés: A munkavállalók a vezetőikkel együtt SMART célokat (Specifikus, Mérhető, 
        Elérhető, Releváns, Időhöz kötött) határoznak meg minden év elején.
        
        Féléves Ellenőrzés: Júniusban informális előrehaladási megbeszélések zajlanak a 
        célok haladásának megvitatására és szükség esetén módosításokra.
        
        Teljesítmény Értékelés: A munkavállalókat 5 fokozatú skálán értékelik: Fejlesztendő, 
        Megfelelő, Jó, Nagyon Jó, Kiemelkedő. Az értékelés közvetlenül befolyásolja az 
        éves bónusz kalkulációt.
        """
    },
    {
        "document_id": "dok-005",
        "ocr_text": """
        2026-os Munkaszüneti Napok
        
        A következő ünnepnapokon fizetett szabadnap jár:
        - Újév: Január 1
        - Nemzeti Ünnep: Március 15
        - Húsvét: Március 31 - Április 1
        - Munka Ünnepe: Május 1
        - Pünkösd: Május 19-20
        - Államalapítás: Augusztus 20
        - Nemzeti Ünnep: Október 23
        - Mindenszentek: November 1
        - Karácsony: December 25-26
        
        Irodazárás: Az iroda december 28-31 között zárva tart az év végi karbantartás miatt.
        A munkavállalók szabadnapot vehetnek ki vagy távmunkázhatnak ebben az időszakban.
        
        Mobil Szabadnapok: Minden munkavállaló évi 2 mobil szabadnapot kap, melyet személyes, 
        kulturális vagy vallási alkalmakkor használhat fel.
        """
    }
]

# Test questions
TEST_QUESTIONS = [
    "Hány napot lehet otthonról dolgozni egy héten?",
    "Mekkora az éves cafeteria keret?"
]


async def store_document(client: httpx.AsyncClient, doc: Dict[str, str]) -> Dict[str, Any]:
    """Store a document via the /store endpoint."""
    print(f"\n📄 Storing document: {doc['document_id']}")
    
    payload = {
        "tenant": TENANT,
        "document_id": doc["document_id"],
        "ocr_text": doc["ocr_text"]
    }
    
    try:
        response = await client.post(f"{BASE_URL}/store", json=payload, timeout=120.0)
        response.raise_for_status()
        result = response.json()
        print(f"   ✅ Stored successfully: {result['chunks_count']} chunks")
        return result
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"error": str(e)}


async def ask_question(client: httpx.AsyncClient, question: str) -> Dict[str, Any]:
    """Ask a question via the /chat endpoint."""
    print(f"\n❓ Question: {question}")
    
    payload = {
        "tenant": TENANT,
        "user_id": USER_ID,
        "messages": [
            {"role": "user", "content": question}
        ]
    }
    
    try:
        response = await client.post(f"{BASE_URL}/chat", json=payload, timeout=120.0)
        response.raise_for_status()
        result = response.json()
        
        print(f"   💬 Answer: {result['answer']}")
        print(f"   📚 Sources: {', '.join(result['document_ids'])}")
        return result
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {"error": str(e)}


async def test_health_check(client: httpx.AsyncClient):
    """Test if the API is running."""
    print("🔍 Checking API health...")
    try:
        response = await client.get(f"{BASE_URL}/")
        response.raise_for_status()
        result = response.json()
        print(f"   ✅ API is running: {result['service']} v{result['version']}")
        return True
    except Exception as e:
        print(f"   ❌ API is not accessible: {e}")
        return False


async def main():
    """Main test execution."""
    print("=" * 80)
    print("RAG Application Test Suite")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Health check
        if not await test_health_check(client):
            print("\n❌ Cannot connect to API. Make sure the server is running.")
            return
        
        # Store documents
        print("\n" + "=" * 80)
        print("1. FÁZIS: Dokumentumok Tárolása")
        print("=" * 80)
        
        store_results = []
        for doc in SAMPLE_DOCUMENTS:
            result = await store_document(client, doc)
            store_results.append(result)
            await asyncio.sleep(1)  # Small delay between requests
        
        total_chunks = sum(r.get('chunks_count', 0) for r in store_results if 'chunks_count' in r)
        print(f"\n✅ {len(SAMPLE_DOCUMENTS)} dokumentum tárolva összesen {total_chunks} darab részlettel")
        
        # Wait a bit for indexing
        print("\n⏳ Várakozás 2 másodpercet az indexelésre...")
        await asyncio.sleep(2)
        
        # Ask questions
        print("\n" + "=" * 80)
        print("2. FÁZIS: Kérdések Feltevése")
        print("=" * 80)
        
        chat_results = []
        for question in TEST_QUESTIONS:
            result = await ask_question(client, question)
            chat_results.append(result)
            await asyncio.sleep(1)  # Small delay between requests
        
        # Summary
        print("\n" + "=" * 80)
        print("TESZT ÖSSZEGZÉS")
        print("=" * 80)
        
        successful_stores = sum(1 for r in store_results if 'chunks_count' in r)
        successful_chats = sum(1 for r in chat_results if 'answer' in r)
        
        print(f"Tárolt dokumentumok: {successful_stores}/{len(SAMPLE_DOCUMENTS)}")
        print(f"Megválaszolt kérdések: {successful_chats}/{len(TEST_QUESTIONS)}")
        
        if successful_stores == len(SAMPLE_DOCUMENTS) and successful_chats == len(TEST_QUESTIONS):
            print("\n🎉 Minden teszt sikeres!")
        else:
            print("\n⚠️  Néhány teszt sikertelen. Ellenőrizd a fenti kimeneteket!")


if __name__ == "__main__":
    asyncio.run(main())
