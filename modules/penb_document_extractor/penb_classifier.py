"""
PENB Energy Performance Document Extractor & Municipal Classifier
Author: Jaroslav Karbusický
Production System: Deployed for Central Bohemian Municipal Energy Audits (EnMS / Pasportizace)

Processes official Building Energy Performance Certificates (PENB - Průkaz energetické náročnosti budovy).
Extracts Czech legal validity windows (10-year limits under Decree 78/2013 Sb.), matches municipal cadastre entities,
and handles OCR artifact recovery using PyMuPDF and regex grammar rules.
"""

import os
import re
import json
import logging
from datetime import datetime, date
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PENBExtractor")

CZECH_MUNICIPALITIES = [
    "Konojedy", "Kostelec nad Černými Lesy", "Kostelní Lhota", "Kouřim",
    "Křečhoř", "Nová Ves I", "Nymburk", "Pečky", "Plaňany", "Poříčany",
    "Sadská", "Tatce", "Třebestovice", "Vitice", "Zásmuky", "Červené Pečky"
]

CZECH_MONTHS = {
    'leden': 1, 'ledna': 1, 'lednu': 1,
    'únor': 2, 'února': 2, 'únoru': 2, 'unor': 2, 'unora': 2,
    'březen': 3, 'března': 3, 'březnu': 3, 'brezen': 3, 'brezna': 3,
    'duben': 4, 'dubna': 4, 'dubnu': 4,
    'květen': 5, 'května': 5, 'květnu': 5, 'kveten': 5, 'kvetna': 5,
    'červen': 6, 'června': 6, 'červnu': 6, 'cerven': 6, 'cervna': 6,
    'červenec': 7, 'července': 7, 'červenci': 7, 'cervenec': 7, 'cervence': 7,
    'srpen': 8, 'srpna': 8, 'srpnu': 8,
    'září': 9, 'zari': 9,
    'říjen': 10, 'října': 10, 'říjnu': 10, 'rijen': 10, 'rijna': 10,
    'listopad': 11, 'listopadu': 11,
    'prosinec': 12, 'prosince': 12, 'prosinci': 12
}


@dataclass
class PENBMetadata:
    document_name: str
    municipality: Optional[str]
    identified_dates: List[str]
    issue_date: Optional[str]
    valid_until: Optional[str]
    is_legally_valid: bool
    energy_rating_class: Optional[str]
    status_notes: str


class PENBTextParser:
    """Parser designed to handle typical Czech OCR artifacts and diacritic issues."""

    @staticmethod
    def normalize_ocr_dates(text: str) -> str:
        # Fix missing spaces in OCR output: e.g. "platnostdo" -> "platnost do"
        text = re.sub(r'platnostod', 'platnost od', text, flags=re.I)
        text = re.sub(r'platnostdo', 'platnost do', text, flags=re.I)
        # Fix OCR misreading 1 as l or I: e.g. 15.I0.2023 -> 15.10.2023
        text = re.sub(r'\b(\d{1,2})\.[Il]([0-2])\.(\d{4})\b', r'\1.1\2.\3', text)
        # Normalize periods and commas in dates
        text = re.sub(r'\b(\d{1,2})[.,\s]+(\d{1,2})[.,\s]+(\d{4})\b', r'\1.\2.\3', text)
        return text

    @classmethod
    def extract_dates(cls, text: str) -> List[Tuple[date, str]]:
        clean_text = cls.normalize_ocr_dates(text)
        dates: List[Tuple[date, str]] = []

        # Standard DD.MM.YYYY
        pattern = r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b'
        for m in re.finditer(pattern, clean_text):
            try:
                d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                ctx = clean_text[max(0, m.start() - 50):min(len(clean_text), m.end() + 50)]
                dates.append((d, ctx.replace('\n', ' ')))
            except ValueError:
                continue

        # Czech verbal months: "15. května 2024"
        pattern_cz = r'\b(\d{1,2})\b\.?\s*([a-zA-Záéíóúýčďěňřšťžůú]+)\s*\b(\d{4})\b'
        for m in re.finditer(pattern_cz, clean_text):
            day = int(m.group(1))
            month_str = m.group(2).lower()
            year = int(m.group(3))
            if month_str in CZECH_MONTHS:
                try:
                    d = date(year, CZECH_MONTHS[month_str], day)
                    ctx = clean_text[max(0, m.start() - 50):min(len(clean_text), m.end() + 50)]
                    dates.append((d, ctx.replace('\n', ' ')))
                except ValueError:
                    continue

        return dates

    @classmethod
    def detect_municipality(cls, text: str) -> Optional[str]:
        for mun in CZECH_MUNICIPALITIES:
            if re.search(r'\b' + re.escape(mun) + r'\b', text, re.IGNORECASE):
                return mun
        return None

    @classmethod
    def detect_energy_class(cls, text: str) -> Optional[str]:
        # Matches Czech energy class indicator: "Třída energetické náročnosti: B" or "třída A / B / C"
        m = re.search(r'(?:třída|trida)\s*(?:energetické\s*náročnosti)?\s*[:\-]?\s*([A-G])\b', text, re.I)
        if m:
            return m.group(1).upper()
        return None

    @classmethod
    def evaluate_certificate(cls, doc_name: str, raw_text: str, reference_date: date = date(2026, 10, 1)) -> PENBMetadata:
        municipality = cls.detect_municipality(raw_text)
        energy_class = cls.detect_energy_class(raw_text)
        dates_with_ctx = cls.extract_dates(raw_text)

        if not dates_with_ctx:
            return PENBMetadata(
                document_name=doc_name,
                municipality=municipality,
                identified_dates=[],
                issue_date=None,
                valid_until=None,
                is_legally_valid=False,
                energy_rating_class=energy_class,
                status_notes="NEURČENO: V dokumentu nebylo nalezeno žádné platné datum.",
            )

        # Check explicit validity expiration
        valid_until: Optional[date] = None
        issue_date: Optional[date] = None

        for d, ctx in dates_with_ctx:
            ctx_lower = ctx.lower()
            if any(k in ctx_lower for k in ['platnost do', 'platnosti do', 'platny do', 'platna do']):
                valid_until = d
            elif any(k in ctx_lower for k in ['vyhotoveno', 'vystaveno', 'zpracovano', 'datum vypracovani']):
                issue_date = d

        # Fallback heuristic: PENB has standard 10-year validity window under Czech law
        is_valid = False
        notes = ""

        if valid_until:
            is_valid = valid_until >= reference_date
            notes = f"Platnost do {valid_until.strftime('%d.%m.%Y')} ({'PLATNÝ' if is_valid else 'PROŠLÝ'})."
        elif issue_date:
            ten_years_ago = date(reference_date.year - 10, reference_date.month, reference_date.day)
            is_valid = issue_date >= ten_years_ago
            notes = f"Datum vyhotovení {issue_date.strftime('%d.%m.%Y')} (10letá lhůta: {'PLATNÝ' if is_valid else 'PROŠLÝ'})."
        else:
            latest = max([d for d, _ in dates_with_ctx])
            is_valid = latest >= date(reference_date.year - 10, reference_date.month, reference_date.day)
            notes = f"Odhad dle nejnovějšího data {latest.strftime('%d.%m.%Y')}."

        return PENBMetadata(
            document_name=doc_name,
            municipality=municipality,
            identified_dates=[d.strftime('%d.%m.%Y') for d, _ in dates_with_ctx],
            issue_date=issue_date.strftime('%d.%m.%Y') if issue_date else None,
            valid_until=valid_until.strftime('%d.%m.%Y') if valid_until else None,
            is_legally_valid=is_valid,
            energy_rating_class=energy_class,
            status_notes=notes,
        )


if __name__ == "__main__":
    # Real-world benchmark test cases based on municipal audit scans
    sample_scans = [
        (
            "PENB_ZSDruzinova_Pecky.pdf",
            "Město Pečky, Základní škola. Průkaz energetické náročnosti budovy ev. č. 14205/2019. "
            "Vyhotoveno dne 14. května 2019. Platnost do 14.05.2029. Třída energetické náročnosti: C - Úsporná."
        ),
        (
            "PENB_ObecniUrad_Vitice.pdf",
            "Obec Vitice, budova č.p. 42. Datum zpracování: 10.11.2014. "
            "Třída energetické náročnosti budovy: D. Osvědčení auditora MPO č. 0481."
        ),
        (
            "PENB_Sokolovna_Krechor.pdf",
            "Obec Křečhoř. Energetický štítek obálky budovy. Datum vystavení: 22.08.2022. "
            "Platnost štítku do 22.08.2032. Třída: B - Velmi úsporná."
        )
    ]

    print("--- BENCHMARK: PENB Municipal Certificate Classifier ---")
    results = []
    for filename, raw_ocr in sample_scans:
        res = PENBTextParser.evaluate_certificate(filename, raw_ocr)
        results.append(asdict(res))
        print(f"[{'VALID' if res.is_legally_valid else 'EXPIRED'}] {res.document_name} | Obec: {res.municipality} | Třída: {res.energy_rating_class} | {res.status_notes}")

    with open("penb_classified_sample.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved sample results to penb_classified_sample.json")
