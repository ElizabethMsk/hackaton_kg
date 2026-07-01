import pdfplumber
import json

# Открываем PDF-файл
print("Читаем PDF...")
with pdfplumber.open("article.pdf") as pdf:
    full_text = ""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n--- Страница {i+1} ---\n{text}"

# Сохраняем извлечённый текст в JSON
with open("text.json", "w", encoding="utf-8") as f:
    json.dump({"text": full_text, "pages": len(pdf.pages)}, f, ensure_ascii=False, indent=2)

print(f"✅ Готово!")
print(f"📄 Страниц: {len(pdf.pages)}")
print(f"📝 Символов: {len(full_text)}")
print(f"\nПервые 300 символов текста:")
print(full_text[:300])