#!/usr/bin/env python3
"""
Olvasási terv konvertáló: MM-DD formátumról számozott napokra (1-366)
"""

import json
from datetime import date, timedelta

# Régi terv beolvasása
with open('data/reading_plan.json', 'r', encoding='utf-8') as f:
    old_plan = json.load(f)

# Új terv készítése
new_plan = {}

# Naptári év napjait végigiterálva konvertáljuk a kulcsokat
# Feltételezzük, hogy a terv január 1-től indul
start_date = date(2024, 1, 1)  # Szökőév, hogy legyen 366 nap

for day_number in range(1, 367):
    current_date = start_date + timedelta(days=day_number - 1)
    old_key = current_date.strftime('%m-%d')
    
    if old_key in old_plan:
        new_plan[str(day_number)] = old_plan[old_key]
        print(f"Nap {day_number}: {old_key} -> átmásolva")

# Új terv mentése
with open('data/reading_plan_numbered.json', 'w', encoding='utf-8') as f:
    json.dump(new_plan, f, ensure_ascii=False, indent=4)

print(f"\nKonvertálás kész! {len(new_plan)} nap átmásolva.")
print(f"Mentve: data/reading_plan_numbered.json")
