import json
import csv
import re

with open("input.json", "r", encoding="utf-8") as f:
    text = f.read()

# Исправляем кавычки внутри name
text = re.sub(
    r'("name"\s*:\s*")(.+?)("(?=\s*,\s*"category"))',
    lambda m: m.group(1) + m.group(2).replace('"', '\\"') + m.group(3),
    text
)

data = json.loads(text)

# Удаляем дубли по id
unique_data = {}
for item in data:
    unique_data[item["id"]] = item

data = list(unique_data.values())

# Создаём CSV без заголовка и BOM
with open("output.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["id", "name", "category"],
        quoting=csv.QUOTE_MINIMAL
    )
    writer.writerows(data)

print(f"Всего записей: {len(data)}")
print(f"Уникальных записей: {len(data)}")
print(f"Удалено дублей: {len(unique_data) - len(data)}")
print("Готово: output.csv")