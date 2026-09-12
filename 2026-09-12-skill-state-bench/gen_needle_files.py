#UP потребность: needle-middle на big-pickle (0 бесплатно опт) в помощь для методики.
# Стратегия: opencode run -f /path/to/needle_file.txt "Какой код доступа указан в файле? Ответь одной строкой, только код."
# -f прикрепляет файл к сообщению: файл PUT в payload - это покажет, как "retrieve info from context".
import json, random, os

os.makedirs(r"C:\Work\llm-wiki\wiki\content\статьи\_dossier-raw\needle_files", exist_ok=True)
for seed in (71, 72, 73, 74):
    random.seed(seed)
    secret = f"{random.randint(1000,9999)}A{random.randint(100,999)}"
    n_lines = int(30000*3.6)//92
    half = (n_lines-1)//2
    lines = [f"Строка журнала {random.randint(0,10**6)}: обработка заявки #{random.randint(10000,99999)} завершена штатно."
             for _ in range(half)]
    lines.append(f"Важная заметка: код доступа {secret}.")
    lines += [f"Строка журнала {random.randint(0,10**6)}: обработка заявки #{random.randint(10000,99999)} завершена штатно."
              for _ in range(n_lines-1-half)]
    with open(rf"C:\Work\llm-wiki\wiki\content\статьи\_dossier-raw\needle_files\needle_{seed}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(seed, secret)
