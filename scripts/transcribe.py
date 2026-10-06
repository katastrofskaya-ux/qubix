#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Расшифровка записи созвона в текст — локально, файл никуда не уходит.

    scripts/transcribe.py запись.mp4
    scripts/transcribe.py запись.m4a --out созвон.txt
    scripts/transcribe.py запись.mp3 --model medium   # точнее, но дольше

Понимает всё, что умеет декодировать PyAV: mp4, m4a, mp3, ogg, wav, mkv.
Из видео звук берётся сам, отдельно выдёргивать не нужно.

Результат — текст с отметками времени, по репликам:
    [00:04:12] Ну вот смотрите, на этом экране кнопка не там стоит...

Модель распознавания живёт в контейнере; запись во внешние сервисы не
отправляется — это важно, потому что на созвонах обсуждается продукт (NDA).
Первый запуск скачивает модель (~500 МБ для small), дальше берёт из кеша.
"""
import argparse, os, sys, time


def hhmmss(seconds):
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    p = argparse.ArgumentParser(description="Расшифровка созвона в текст")
    p.add_argument("audio", help="файл записи: mp4, m4a, mp3, ogg, wav, mkv")
    p.add_argument("--out", help="куда положить текст (по умолчанию рядом, .txt)")
    p.add_argument("--model", default="small",
                   help="tiny | base | small (по умолчанию) | medium | large-v3; "
                        "крупнее — точнее и дольше")
    p.add_argument("--lang", default="ru", help="язык записи (по умолчанию ru)")
    args = p.parse_args()

    if not os.path.exists(args.audio):
        sys.exit(f"файла нет: {args.audio}")

    from faster_whisper import WhisperModel

    print(f"Модель {args.model} готовится…", flush=True)
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    started = time.time()
    segments, info = model.transcribe(
        args.audio, language=args.lang, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 700})
    print(f"Длина записи: {hhmmss(info.duration)}. Пошла расшифровка…", flush=True)

    out_path = args.out or os.path.splitext(args.audio)[0] + ".txt"
    lines = []
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Расшифровка: {os.path.basename(args.audio)}\n")
        f.write(f"# Длина {hhmmss(info.duration)}, язык {info.language}\n\n")
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            line = f"[{hhmmss(seg.start)}] {text}"
            f.write(line + "\n")
            lines.append(line)
            # Показываем ход работы: длинную запись видно, что она идёт.
            if len(lines) % 25 == 0:
                print(f"  …{hhmmss(seg.start)}", flush=True)

    spent = int(time.time() - started)
    print(f"\nГотово за {hhmmss(spent)}: {len(lines)} реплик → {out_path}")


if __name__ == "__main__":
    main()
