"""
AI Automation & Data Systems - Main Orchestrator
Author: Jaroslav Karbusický
Portfolio for: Clientelo (Junior AI Developer)

Central entry point demonstrating production-grade data pipelines:
- Module 1: ARES & Enerkom Energy Community Lead Enrichment
- Module 2: PENB Energy Performance Document OCR & Classifier (Municipal Audits)
- Module 3: OpenDescript Audio/Video Transcription & Word Timings
- Module 4: Web & Forum Lead Signal Harvester
"""

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        description="Jaroslav Karbusický - AI Automation & Data Engineering Suite"
    )
    parser.add_argument(
        "--module",
        choices=["ares", "penb", "media", "web", "all"],
        default="ares",
        help="Pipeline module to execute (default: ares)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("   AI AUTOMATION & DATA ENGINEERING SUITE")
    print("   Author: Jaroslav Karbusický (Digitální podnikání, UPCE)")
    print("=" * 70)

    if args.module in ["ares", "all"]:
        print("\n[MODULE 1] Running ARES & Enerkom Lead Enrichment Pipeline...")
        from modules.ares_registry_pipeline.ares_lead_enricher import AresClient, EnerkomLeadPipeline
        candidates = [
            {"ico": "27082440", "name_hint": "Alza.cz", "license_type": "FVE / Commercial Rooftop", "capacity_kw": 480.0, "district": "Praha-Holešovice"},
            {"ico": "00005886", "name_hint": "Škoda Auto", "license_type": "Industrial Cogeneration", "capacity_kw": 2400.0, "district": "Mladá Boleslav"},
            {"ico": "26177005", "name_hint": "ČEZ Distribuce", "license_type": "Grid Interconnect", "capacity_kw": 1250.0, "district": "Děčín"},
        ]
        client = AresClient(delay_sec=0.2)
        pipeline = EnerkomLeadPipeline(client)
        leads = pipeline.process_batch(candidates)
        pipeline.export_csv(leads, "enriched_leads.csv")
        pipeline.export_json(leads, "enriched_leads.json")
        print(f" -> Completed ARES module. Exported {len(leads)} leads.")

    if args.module in ["penb", "all"]:
        print("\n[MODULE 2] Running PENB Document Classifier (Pasportizace / Municipal)...")
        from modules.penb_document_extractor.penb_classifier import PENBTextParser
        sample_scans = [
            ("PENB_ZSDruzinova_Pecky.pdf", "Město Pečky. Platnost do 14.05.2029. Třída B."),
            ("PENB_ObecniUrad_Vitice.pdf", "Obec Vitice. Datum zpracování: 10.11.2014. Třída D."),
        ]
        for name, text in sample_scans:
            res = PENBTextParser.evaluate_certificate(name, text)
            print(f" -> {name}: {'PLATNÝ' if res.is_legally_valid else 'PROŠLÝ'} (Obec: {res.municipality})")

    if args.module in ["media", "all"]:
        print("\n[MODULE 3] Running OpenDescript Media Transcription Engine...")
        from modules.opendescript_transcription.transcriber_engine import MediaTranscriptionEngine, TranscriptSegment, WordTiming
        sample = [
            TranscriptSegment(1, 0, 0.0, 2.5, "Ukázka synchronizace textu s audiem.", [WordTiming("Ukázka", 0.0, 0.5, 0.98)])
        ]
        engine = MediaTranscriptionEngine()
        engine.export_srt(sample, "sample_captions.srt")
        print(" -> Completed OpenDescript subtitle export.")

    if args.module in ["web", "all"]:
        print("\n[MODULE 4] Running Web Lead Signal Harvester...")
        from modules.web_lead_harvester.rss_harvester import LeadSignalHarvester
        signals = LeadSignalHarvester.harvest_channel("B2B", "smallbusiness", max_items=2)
        print(f" -> Harvested {len(signals)} live signals from r/smallbusiness.")

    print("\n" + "=" * 70)
    print("Execution complete. All pipelines healthy.")
    print("=" * 70)

if __name__ == "__main__":
    main()
