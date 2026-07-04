import requests

# Вставьте ключ напрямую (без пробелов!)
API_KEY = "AQVNw7CdQeUcg4FgFp5bOZU6ojLPTM5FOVGjsiHP"
FOLDER_ID = "b1ggusvist6c2sia1dno"

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Api-Key {API_KEY}"
}

payload = {
    "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.1,
        "maxTokens": 50
    },
    "messages": [
        {"role": "user", "text": "Привет"}
    ]
}

print("Тестирование API...")
response = requests.post(url, headers=headers, json=payload)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print("✅ API ключ работает!")
    result = response.json()
    print("Ответ:", result["result"]["alternatives"][0]["message"]["text"])
else:
    print("❌ Ошибка:")
    print(response.text)