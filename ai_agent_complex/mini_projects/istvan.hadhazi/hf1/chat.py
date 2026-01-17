#!/usr/bin/env python3
"""
AI Chat Console - OpenAI Chat Interface
Egyszerű konzol alapú chat alkalmazás OpenAI GPT-4 modellel.
"""

import os
import sys
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

# Színes konzol kimenet támogatás
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_ENABLED = True
except ImportError:
    COLORS_ENABLED = False
    # Fallback ha nincs colorama
    class Fore:
        GREEN = ""
        BLUE = ""
        YELLOW = ""
        RED = ""
        CYAN = ""
    
    class Style:
        RESET_ALL = ""
        BRIGHT = ""


class ChatConsole:
    """Interaktív chat konzol osztály"""
    
    def __init__(self):
        """Inicializálás"""
        # Környezeti változók betöltése
        load_dotenv()
        
        # OpenAI konfiguráció
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print(f"{Fore.RED}HIBA: OPENAI_API_KEY nincs beállítva a .env fájlban!{Style.RESET_ALL}")
            sys.exit(1)
        
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        
        # OpenAI kliens inicializálása
        self.client = OpenAI(api_key=self.api_key)
        
        # Chat history
        self.messages: List[Dict[str, str]] = []
        
        print(f"{Fore.GREEN}✓ OpenAI API kapcsolat létrehozva{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Model: {self.model}{Style.RESET_ALL}")
    
    def print_header(self):
        """Fejléc megjelenítése"""
        print("\n" + "=" * 43)
        print(f"{Fore.CYAN}{Style.BRIGHT}   AI Chat Console - OpenAI {self.model}{Style.RESET_ALL}")
        print("=" * 43)
        print("\nParancsok:")
        print("  - Írj be bármilyen kérdést")
        print(f"  - {Fore.YELLOW}'exit'{Style.RESET_ALL} vagy {Fore.YELLOW}'quit'{Style.RESET_ALL} - Kilépés")
        print(f"  - {Fore.YELLOW}'clear'{Style.RESET_ALL} - Beszélgetés törlése")
        print(f"  - {Fore.YELLOW}'history'{Style.RESET_ALL} - Korábbi üzenetek")
        print("\n" + "-" * 43 + "\n")
    
    def chat(self, user_message: str) -> str:
        """
        Üzenet küldése az OpenAI API-nak és válasz fogadása
        
        Args:
            user_message: Felhasználó üzenete
            
        Returns:
            AI válasza
        """
        # Üzenet hozzáadása a history-hoz
        self.messages.append({"role": "user", "content": user_message})
        
        try:
            # OpenAI API hívás
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Válasz kinyerése
            assistant_message = response.choices[0].message.content
            
            # Válasz hozzáadása a history-hoz
            self.messages.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            error_msg = f"Hiba történt: {str(e)}"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            # Ha hiba történt, távolítsuk el a felhasználó utolsó üzenetét
            if self.messages and self.messages[-1]["role"] == "user":
                self.messages.pop()
            return error_msg
    
    def show_history(self):
        """Chat history megjelenítése"""
        if not self.messages:
            print(f"{Fore.YELLOW}Még nincsenek üzenetek.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}--- Chat History ---{Style.RESET_ALL}")
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                print(f"{Fore.GREEN}You:{Style.RESET_ALL} {content}")
            else:
                print(f"{Fore.BLUE}Assistant:{Style.RESET_ALL} {content}")
        print()
    
    def clear_history(self):
        """Chat history törlése"""
        self.messages = []
        print(f"{Fore.YELLOW}Beszélgetés törölve.{Style.RESET_ALL}\n")
    
    def run(self):
        """Fő alkalmazás loop"""
        self.print_header()
        
        while True:
            try:
                # Felhasználói input
                user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}").strip()
                
                # Üres input kezelése
                if not user_input:
                    continue
                
                # Parancsok kezelése
                if user_input.lower() in ["exit", "quit"]:
                    print(f"\n{Fore.CYAN}Viszlát!{Style.RESET_ALL}\n")
                    break
                
                if user_input.lower() == "clear":
                    self.clear_history()
                    continue
                
                if user_input.lower() == "history":
                    self.show_history()
                    continue
                
                # Chat üzenet küldése
                print(f"{Fore.BLUE}Assistant:{Style.RESET_ALL} ", end="", flush=True)
                response = self.chat(user_input)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print(f"\n\n{Fore.CYAN}Kilépés...{Style.RESET_ALL}\n")
                break
            except EOFError:
                print(f"\n\n{Fore.CYAN}Viszlát!{Style.RESET_ALL}\n")
                break
            except Exception as e:
                print(f"{Fore.RED}Váratlan hiba: {e}{Style.RESET_ALL}")


def main():
    """Fő belépési pont"""
    try:
        console = ChatConsole()
        console.run()
    except Exception as e:
        print(f"{Fore.RED}Indítási hiba: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()

