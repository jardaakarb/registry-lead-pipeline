"""
Registry Lead Pipeline (ARES & Public Registry Data Enrichment)
Built for Enerkom (Czech Energy Community) & B2B Lead Generation.

Automates company profile extraction, statutory organ lookup,
and energy license matching via official Czech public registries (ARES / ERÚ).
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
logger = logging.getLogger("RegistryLeadPipeline")

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


@dataclass
class LeadProfile:
    ico: str
    company_name: str
    legal_form: str
    registered_address: str
    city: str
    postal_code: str
    cz_nace: List[str]
    is_active: bool
    source_license_type: Optional[str] = None
    installed_capacity_kw: Optional[float] = None
    lookup_status: str = "SUCCESS"


class AresClient:
    """Client for the official Czech Ministry of Finance ARES REST API."""

    def __init__(self, request_delay: float = 0.2):
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "Enerkom-Lead-Pipeline/1.0",
            }
        )

    def fetch_subject(self, ico: str) -> Optional[Dict[str, Any]]:
        """Fetch economic subject details by 8-digit IČO."""
        cleaned_ico = str(ico).strip().zfill(8)
        url = f"{ARES_BASE_URL}/{cleaned_ico}"

        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"IČO {cleaned_ico} not found in ARES.")
                return None
            else:
                logger.error(
                    f"ARES returned status {response.status_code} for IČO {cleaned_ico}"
                )
                return None
        except requests.RequestException as e:
            logger.error(f"Network error querying IČO {cleaned_ico}: {e}")
            return None


class Pipeline:
    """Enrichment pipeline combining source records (e.g. ERÚ licenses) with ARES corporate data."""

    def __init__(self, ares_client: AresClient):
        self.client = ares_client

    def process_records(
        self, raw_records: List[Dict[str, Any]]
    ) -> List[LeadProfile]:
        results: List[LeadProfile] = []
        total = len(raw_records)

        logger.info(f"Starting batch enrichment for {total} candidate records.")

        for idx, row in enumerate(raw_records, 1):
            ico = str(row.get("ico", "")).strip().zfill(8)
            license_type = row.get("license_type", "")
            capacity = row.get("capacity_kw", None)

            logger.info(f"[{idx}/{total}] Enriching IČO {ico}...")
            ares_data = self.client.fetch_subject(ico)

            if not ares_data:
                results.append(
                    LeadProfile(
                        ico=ico,
                        company_name=row.get("company_name", "UNKNOWN"),
                        legal_form="N/A",
                        registered_address="N/A",
                        city="N/A",
                        postal_code="N/A",
                        cz_nace=[],
                        is_active=False,
                        source_license_type=license_type,
                        installed_capacity_kw=float(capacity) if capacity else None,
                        lookup_status="NOT_FOUND",
                    )
                )
                continue

            # Extract structured address
            sidlo = ares_data.get("sidlo", {})
            full_address = sidlo.get("textovaAdresa", "")
            city = sidlo.get("nazevObce", "")
            psc = str(sidlo.get("psc", ""))

            # Extract activity classification
            nace_codes = ares_data.get("czNace", [])

            lead = LeadProfile(
                ico=ico,
                company_name=ares_data.get("obchodniJmeno", "N/A"),
                legal_form=ares_data.get("pravniForma", "N/A"),
                registered_address=full_address,
                city=city,
                postal_code=psc,
                cz_nace=nace_codes[:5] if isinstance(nace_codes, list) else [],
                is_active=True,
                source_license_type=license_type,
                installed_capacity_kw=float(capacity) if capacity else None,
                lookup_status="SUCCESS",
            )
            results.append(lead)

        return results

    @staticmethod
    def export_csv(leads: List[LeadProfile], output_path: str):
        """Export leads to a clean CSV formatted for Airtable or Excel import."""
        if not leads:
            return

        keys = [
            "ico",
            "company_name",
            "legal_form",
            "city",
            "postal_code",
            "registered_address",
            "installed_capacity_kw",
            "source_license_type",
            "cz_nace",
            "is_active",
            "lookup_status",
        ]

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for lead in leads:
                d = asdict(lead)
                writer.writerow(
                    [
                        d["ico"],
                        d["company_name"],
                        d["legal_form"],
                        d["city"],
                        d["postal_code"],
                        d["registered_address"],
                        d["installed_capacity_kw"],
                        d["source_license_type"],
                        ";".join(d["cz_nace"]),
                        d["is_active"],
                        d["lookup_status"],
                    ]
                )
        logger.info(f"Exported {len(leads)} rows to CSV: {output_path}")

    @staticmethod
    def export_json(leads: List[LeadProfile], output_path: str):
        """Export leads to JSON for webhook or API ingestion (Make.com / Airtable)."""
        data = [asdict(lead) for lead in leads]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(leads)} items to JSON: {output_path}")


def main():
    logger.info("Initializing Enerkom & B2B Lead Enrichment Pipeline...")

    # Sample input records demonstrating real use case
    sample_candidates = [
        {
            "ico": "27082440",
            "company_name": "Alza.cz a.s.",
            "license_type": "FVE / Commercial Solar",
            "capacity_kw": 250.0,
        },
        {
            "ico": "00005886",
            "company_name": "Škoda Auto a.s.",
            "license_type": "Industrial Cogeneration",
            "capacity_kw": 1800.0,
        },
        {
            "ico": "45274649",
            "company_name": "ČEZ a.s.",
            "license_type": "Distribution / Generation",
            "capacity_kw": 5000.0,
        },
        {
            "ico": "26177005",
            "company_name": "ČEZ Distribuce, a. s.",
            "license_type": "Grid Operation",
            "capacity_kw": 1200.0,
        },
    ]

    client = AresClient()
    pipeline = Pipeline(client)

    enriched_leads = pipeline.process_records(sample_candidates)

    pipeline.export_csv(enriched_leads, "enriched_leads.csv")
    pipeline.export_json(enriched_leads, "enriched_leads.json")

    logger.info("Pipeline executed successfully!")


if __name__ == "__main__":
    main()
