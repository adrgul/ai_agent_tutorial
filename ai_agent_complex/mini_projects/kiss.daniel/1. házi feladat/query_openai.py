#!/usr/bin/env python3
"""Egyszerű CLI script Groq Chat API híváshoz.

Használat:
  - Parancsori argumentumként: 
      python3 query_openai.py "Mondd el röviden, mi a Python list comprehension"
  - Pipe-olt stdin-ből:
      echo "Írj egy rövid idézetet" | python3 query_openai.py
  - API kulcs: .env fájlból (mini_projects/kiss.daniel/.env) vagy --api-key opcióval

Követelmények:
  pip install groq
"""
import os
import sys
import argparse

try:
    from groq import Groq
except Exception:
    print("Hiányzik a 'groq' csomag. Telepítsd: pip install groq", file=sys.stderr)
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Egyszerű script Groq Chat API híváshoz. A promptot parancssorból adhatod meg vagy be lehet olvasni stdin-ről."
    )
    parser.add_argument('prompt', nargs='*', help='A prompt szövege (ha nincs, beolvassa stdin vagy interaktívan kéri)')
    parser.add_argument('--api-key', '-k', help='Groq API kulcs (ha nincs, a mini_projects/kiss.daniel/.env fájlból tölti be)')
    parser.add_argument('--model', '-m', default='llama-3.3-70b-versatile', help='Használandó modell (alap: llama-3.3-70b-versatile)')
    parser.add_argument('--system', '-s', help='Opcionális system prompt')
    return parser.parse_args()


def main():
    args = parse_args()

    api_key = args.api_key

    # Ha nincs --api-key, betöltjük a kulcsot a `mini_projects/kiss.daniel/.env` fájlból
    if not api_key:
        try:
            from pathlib import Path

            script_dir = Path(__file__).resolve().parent
            env_file = script_dir.parent / '.env'
            if env_file.exists():
                with env_file.open('r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == 'GROQ_API_KEY':
                                api_key = v.strip().strip('"').strip("'")
                                break
        except Exception as e:
            # Ha bármi hiba történik, továbbhaladunk a korábbi hibakezeléssel
            pass

    if not api_key:
        print("Nem található Groq API kulcs a mini_projects/kiss.daniel/.env fájlban. Add meg --api-key paraméterrel vagy hozd létre a .env fájlt a GROQ_API_KEY kulccsal.", file=sys.stderr)
        sys.exit(2)

    client = Groq(api_key=api_key)

    if args.prompt:
        prompt = ' '.join(args.prompt)
    else:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            prompt = ""

    # Ha még mindig nincs prompt, interaktívan kérjük be
    if not prompt:
        try:
            prompt = input("Írd be a promptot: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNincs prompt megadva. Kilépés.", file=sys.stderr)
            sys.exit(3)
    
    if not prompt:
        print("Nincs prompt megadva. Kilépés.", file=sys.stderr)
        sys.exit(3)

    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = client.chat.completions.create(model=args.model, messages=messages)
        content = resp.choices[0].message.content
        print(content)
    except Exception as e:
        print("Hiba a Groq API hívásakor:", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
