# scripts/build_calendar_2026.py
import csv
from datetime import date, timedelta

OUT_CSV = "calendar_2026.csv"

# Intervalos (do seu print)
SEMESTERS = [
    ("2026-02-19", "2026-05-29", "SEMESTRE_I"),
    ("2026-06-01", "2026-09-11", "SEMESTRE_II"),
    ("2026-09-14", "2026-12-16", "SEMESTRE_III"),
]

# Feriados / pontos (do seu print) — ajuste se precisar
# Formato: "AAAA-MM-DD": ("TIPO", "OBS")
HOLIDAYS = {
    "2026-01-01": ("FERIADO", "Confraternização Universal"),
    "2026-02-16": ("PONTO_FACULTATIVO", "Carnaval"),
    "2026-02-18": ("PONTO_FACULTATIVO", "Carnaval"),
    "2026-04-03": ("FERIADO", "Paixão de Cristo"),
    "2026-04-21": ("FERIADO", "Tiradentes"),
    "2026-05-01": ("FERIADO", "Dia do(a) Trabalhador(a)"),
    "2026-05-14": ("FERIADO", "Aniversário de Seabra"),
    "2026-06-04": ("FERIADO", "Corpus Christi"),
    "2026-07-02": ("FERIADO", "Independência da Bahia"),
    "2026-09-07": ("FERIADO", "Independência do Brasil"),
    "2026-10-12": ("FERIADO", "Padroeira do Brasil"),
    "2026-10-28": ("PONTO_FACULTATIVO", "Servidor(a) Público(a)"),
    "2026-11-02": ("FERIADO", "Finados"),
    "2026-11-15": ("FERIADO", "Proclamação da República"),
    "2026-11-20": ("FERIADO", "Consciência Negra"),
    "2026-12-08": ("FERIADO", "N. Sra. da Conceição"),
    "2026-12-24": ("FERIADO", "Natal (véspera)"),
    "2026-12-25": ("FERIADO", "Natal"),
}

def daterange(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

def is_weekday(d: date) -> bool:
    # Monday=0 ... Sunday=6
    return d.weekday() <= 4

def main():
    rows = []
    for start_s, end_s, sem in SEMESTERS:
        y, m, d = map(int, start_s.split("-"))
        start = date(y, m, d)
        y, m, d = map(int, end_s.split("-"))
        end = date(y, m, d)

        for day in daterange(start, end):
            iso = day.isoformat()

            # regra base
            letivo = is_weekday(day)
            kind = "AULA_NORMAL" if letivo else "NAO_LETIVO"
            note = sem

            # sobrescreve se for feriado/ponto
            if iso in HOLIDAYS:
                letivo = False
                kind, extra = HOLIDAYS[iso]
                note = f"{extra} | {sem}"

            rows.append({
                "data": iso,
                "letivo": "sim" if letivo else "nao",
                "tipo": kind,
                "observacao": note,
            })

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["data", "letivo", "tipo", "observacao"])
        w.writeheader()
        w.writerows(rows)

    print(f"OK: gerado {OUT_CSV} com {len(rows)} linhas")

if __name__ == "__main__":
    main()