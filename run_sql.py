"""
run_sql.py
==========
Nástroj pro přímé spouštění SQL skriptů na databázi SQLite.

Použití:
    python run_sql.py <sql_soubor>

Příklady:
    python run_sql.py sql/create.sql        # Vytvoří tabulky
    python run_sql.py sql/insert.sql        # Vloží vzorová data
    python run_sql.py sql/select.sql        # Spustí SELECT dotazy (výsledky se nezobrazí)
    python run_sql.py sql/update_delete.sql # Spustí UPDATE/DELETE příkazy

Poznámka:
    Databáze se nachází v instance/users.db — tuto cestu vytváří Flask
    automaticky při prvním spuštění app.py. Ujistěte se, že složka
    instance/ existuje (tj. nejprve spusťte python app.py).
"""

import sqlite3
import sys


def execute_sql_file(db_name: str, sql_file: str) -> None:
    """
    Spustí všechny SQL příkazy ze zadaného souboru na databázi.

    Používá cursor.executescript() — vhodné pro DDL (CREATE, DROP)
    i DML (INSERT, UPDATE, DELETE) příkazy v jednom souboru.
    Transakce se automaticky potvrdí (COMMIT) po úspěšném provedení.
    Při chybě se vypíše popis a spojení se korektně uzavře.

    Args:
        db_name: Cesta k SQLite databázovému souboru (např. 'instance/users.db').
        sql_file: Cesta k souboru s SQL příkazy.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        # Načtení celého SQL souboru jako řetězce
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # executescript() spustí všechny příkazy v souboru najednou
        # a automaticky provede COMMIT po každém příkazu
        cursor.executescript(sql_script)
        conn.commit()
        print(f"✅ Skript {sql_file} byl úspěšně proveden.")

    except Exception as e:
        print(f"❌ Chyba při provádění {sql_file}: {e}")

    finally:
        # Spojení se vždy uzavře — i při výjimce (finally blok)
        conn.close()


if __name__ == "__main__":
    # Kontrola argumentů příkazové řádky
    if len(sys.argv) < 2:
        print("Použití: python run_sql.py <sql_soubor>")
        print("Příklad: python run_sql.py create.sql")
        sys.exit(1)

    # Spuštění SQL skriptu na databázi.
    # Flask vytváří instance/ složku relativně k app.py v kořeni projektu.
    execute_sql_file("instance/users.db", sys.argv[1])