import requests
import sys

# --- FÜGGVÉNYEK (TOOLS) ---

def get_bitcoin_price():
    """
    Lekérdezi a Bitcoin aktuális árfolyamát a CoinGecko ingyenes API-ról.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10) # Timeout beállítása jó szokás
        response.raise_for_status() # Hiba dobása, ha pl. 404 vagy 500 a válasz
        data = response.json()
        price = data['bitcoin']['usd']
        return f"💰 A Bitcoin jelenlegi árfolyama: ${price:,}" # Ezres elválasztó formázás
    except requests.exceptions.RequestException as e:
        return f"❌ Hiba történt a hálózati kapcsolatban: {e}"

def get_random_joke():
    """
    Lekérdez egy véletlenszerű programozós viccet.
    """
    url = "https://official-joke-api.appspot.com/jokes/programming/random"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Az API egy listát ad vissza, amiben egy elem van
        joke = data[0] 
        return f"😂 Vicc:\n- {joke['setup']}\n- {joke['punchline']}"
    except Exception as e:
        return f"❌ Sajnos most nem tudok vicces lenni: {e}"

# --- ÁGENS LOGIKA (BRAIN) ---

def mini_agent():
    print("\n🤖 --- HÁZI FELADAT ÁGENS --- 🤖")
    print("Mondd meg mit szeretnél: 'árfolyam' (crypto) vagy 'vicc' (szórakozás)?")
    print("Kilépéshez írd be: 'exit'")

    while True:
        print("\n" + "-"*30)
        user_input = input("👤 Te: ").strip().lower()

        if user_input in ['exit', 'kilepes', 'quit']:
            print("🤖 Viszlát!")
            break

        # Routing logika: kulcsszavak alapján döntünk
        if "crypto" in user_input or "bitcoin" in user_input or "árfolyam" in user_input:
            print("🤖 Értettem, lekérdezem az adatokat...")
            result = get_bitcoin_price()
            print(result)
        
        elif "vicc" in user_input or "joke" in user_input or "nevetni" in user_input:
            print("🤖 Rendben, keresek egy jót...")
            result = get_random_joke()
            print(result)
            
        else:
            # Fallback ág: ha nem értjük
            print("🤖 Bocsánat, ezt nem értettem. Próbáld így: 'mennyi a bitcoin' vagy 'mondj egy viccet'.")

# --- INDÍTÁS ---

if __name__ == "__main__":
    # Ellenőrizzük, hogy telepítve van-e a requests
    if 'requests' not in sys.modules:
        import subprocess
        print("⚠️ A 'requests' csomag hiányzik. Telepítés...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        print("✅ Telepítés kész! Kérlek indítsd újra a programot.")
    else:
        mini_agent()