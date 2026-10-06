"""
ARES Registry & Enerkom Lead Enrichment Engine
Author: Jaroslav Karbusický
Production Use-Case: Enerkom (Czech Community Energy - 2 MW Commercial Acquisition)

Connects raw energy license datasets (ERÚ) with the official Czech Ministry of Finance
REST API (ARES) to extract verified company identities, statutory structures, and NACE codes.
"""

import csv
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AresLeadEnricher")

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


@dataclass
class EnrichedLead:
    ico: str
    company_name: str
    legal_form: str
    legal_form_code: Optional[int]
    registered_address: str
    city: str
    postal_code: str
    cz_nace: List[str]
    is_active: bool
    source_license_type: str
    installed_capacity_kw: float
    district: str
    lookup_status: str


class AresClient:
    """Robust client for the Czech official ARES REST API with rate limiting and retry logic."""

    def __init__(self, delay_sec: float = 0.25):
        self.delay_sec = delay_sec
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "Enerkom-Acquisition-Pipeline/2.1 (contact: jara.karbusicky@gmail.com)",
            }
        )

    def get_company_by_ico(self, ico: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        cleaned_ico = str(ico).strip().zfill(8)
        url = f"{ARES_BASE_URL}/{cleaned_ico}"

        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(self.delay_sec)
                resp = self.session.get(url, timeout=12)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 404:
                    logger.warning(f"IČO {cleaned_ico} not registered in ARES.")
                    return None
                elif resp.status_code == 429:
                    logger.warning("Rate limit hit from ARES, backing off...")
                    time.sleep(1.5 * attempt)
                else:
                    logger.error(f"ARES returned status {resp.status_code} for IČO {cleaned_ico}")
            except requests.RequestException as e:
                logger.error(f"Attempt {attempt}: Network error for IČO {cleaned_ico}: {e}")
                time.sleep(1.0)

        return None


class EnerkomLeadPipeline:
    """Orchestrates license matching, corporate profile lookup, and export."""

    def __init__(self, client: AresClient):
        self.client = client

    def process_batch(self, candidate_records: List[Dict[str, Any]]) -> List[EnrichedLead]:
        leads: List[EnrichedLead] = []
        total = len(candidate_records)
        logger.info(f"Processing batch of {total} commercial energy license records...")

        for idx, rec in enumerate(candidate_records, 1):
            ico = str(rec.get("ico", "")).strip().zfill(8)
            lic_type = rec.get("license_type", "Commercial Solar (FVE)")
            cap_kw = float(rec.get("capacity_kw", 0.0))
            district = rec.get("district", "Středočeský kraj")

            logger.info(f"[{idx}/{total}] Querying ARES for IČO {ico} (Capacity: {cap_kw} kW)...")
            ares_data = self.client.get_company_by_ico(ico)

            if not ares_data:
                leads.append(
                    EnrichedLead(
                        ico=ico,
                        company_name=rec.get("name_hint", "UNKNOWN"),
                        legal_form="N/A",
                        legal_form_code=None,
                        registered_address="N/A",
                        city="N/A",
                        postal_code="N/A",
                        cz_nace=[],
                        is_active=False,
                        source_license_type=lic_type,
                        installed_capacity_kw=cap_kw,
                        district=district,
                        lookup_status="NOT_FOUND",
                    )
                )
                continue

            sidlo = ares_data.get("sidlo", {})
            full_address = sidlo.get("textovaAdresa", "")
            city = sidlo.get("nazevObce", "")
            psc = str(sidlo.get("psc", ""))
            pravni_forma = ares_data.get("pravniForma", "")
            nace_list = ares_data.get("czNace", [])

            lead = EnrichedLead(
                ico=ico,
                company_name=ares_data.get("obchodniJmeno", "N/A"),
                legal_form=pravni_forma,
                legal_form_code=ares_data.get("pravniFormaKod"),
                registered_address=full_address,
                city=city,
                postal_code=psc,
                cz_nace=nace_list[:4] if isinstance(nace_list, list) else [],
                is_active=True,
                source_license_type=lic_type,
                installed_capacity_kw=cap_kw,
                district=district,
                lookup_status="SUCCESS",
            )
            leads.append(lead)

        return leads

    def export_csv(self, leads: List[EnrichedLead], filepath: str) -> None:
        if not leads:
            return
        keys = list(asdict(leads[0]).keys())
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for lead in leads:
                d = asdict(lead)
                row = [";".join(d[k]) if isinstance(d[k], list) else d[k] for k in keys]
                writer.writerow(row)
        logger.info(f"Saved {len(leads)} enriched leads to CSV: {filepath}")

    def export_json(self, leads: List[EnrichedLead], filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(l) for l in leads], f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(leads)} enriched leads to JSON: {filepath}")


if __name__ == "__main__":
    # Real test batch for Enerkom Community Acquisition (Středočeský kraj & Commercial Plants)
    candidates = [
        {"ico": "27082440", "name_hint": "Alza.cz", "license_type": "FVE / Commercial Rooftop", "capacity_kw": 480.0, "district": "Praha-Holešovice"},
        {"ico": "00005886", "name_hint": "Škoda Auto", "license_type": "Industrial Cogeneration", "capacity_kw": 2400.0, "district": "Mladá Boleslav"},
        {"ico": "26177005", "name_hint": "ČEZ Distribuce", "license_type": "Distribution Grid Interconnect", "capacity_kw": 1250.0, "district": "Děčín"},
        {"ico": "45274649", "name_hint": "ČEZ a.s.", "license_type": "Utility Scale Generation", "capacity_kw": 5000.0, "district": "Praha"},
        {"ico": "27110591", "name_hint": "Komerční FVE Poděbrady", "license_type": "Solar Park Ground Mount", "capacity_kw": 850.0, "district": "Nymburk / Poděbrady"},
        {"ico": "61672033", "name_hint": "Průmyslový Areál Kolín", "license_type": "FVE Warehouse Rooftop", "capacity_kw": 320.0, "district": "Kolín"},
    ]

    client = AresClient(delay_sec=0.2)
    pipeline = EnerkomLeadPipeline(client)
    enriched = pipeline.process_batch(candidates)
    pipeline.export_csv(enriched, "enriched_leads.csv")
    pipeline.export_json(enriched, "enriched_leads.json")
    print(f"\n[Done] Processed {len(enriched)} leads successfully.")
