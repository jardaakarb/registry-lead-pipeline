# ⚡ Production AI Automation & Data Engineering Suite

**Author:** Jaroslav Karbusický  
**Focus:** AI-Assisted Development, Data Extraction Pipelines, Public Registries (ARES / ERÚ), OCR Document Auditing & Multimodal Systems.  
**Education:** Univerzita Pardubice (FES) – *Digitální podnikání* (Digital Business & AI)  
**Contact:** `jara.karbusicky@gmail.com` | [+420 606 068 340](tel:+420606068340) | [LinkedIn](https://linkedin.com/in/jaroslavkarbusicky)

---

## 🎯 Engineering Philosophy: The AI Operator Mindset

> *"I don't spend weeks hand-typing boilerplate syntax from memory. I operate as an AI-driven systems builder: I define data architectures, guide and verify AI coding agents, validate against dirty real-world public data, debug edge cases, and ship working solutions directly into production."*

This repository gathers four real-world production data systems I designed and deployed to solve tangible business, energy, and multimedia challenges.

---

## 🏗️ System Architecture Overview

```mermaid
flowchart TD
    subgraph S1 ["1. B2B Lead & Registry Pipeline (Enerkom)"]
        E1["ERÚ Energy Licenses"] --> A1["ARES REST API Client"]
        A1 --> A2["Lead Normalizer & CZ-NACE"]
        A2 --> A3["Airtable / CSV Export (Sales Ready)"]
    end

    subgraph S2 ["2. Municipal Document OCR Engine (Pasportizace)"]
        P1["Municipal Scans (PENB PDFs)"] --> P2["PyMuPDF & Tesseract OCR"]
        P2 --> P3["Czech Date Grammar & Law 78/2013 Heuristics"]
        P3 --> P4["Validity & Municipal Audit Report"]
    end

    subgraph S3 ["3. OpenDescript AI Media Engine"]
        M1["Raw Audio / Video"] --> M2["faster-whisper (GPU/CPU fallback)"]
        M2 --> M3["Word-Level Alignment & Silence Stripping"]
        M3 --> M4["Interactive Text Timeline & SRT"]
    end

    subgraph S4 ["4. Live Web Signal Harvester"]
        W1["Live RSS / XML Streams"] --> W2["Deduplicator & Filter"]
        W2 --> W3["Structured Signal Feed"]
    end
```

---

## 📂 Production Modules in Detail

### 1. `modules/ares_registry_pipeline` — Enerkom Energy Community Lead Engine
* **The Real Business Context:** Developed for **Enerkom** (a Czech energy community with 90+ active members). The community faces a strict milestone: acquire at least **2 MW of commercial renewable capacity** before its general assembly (*valná hromada*).
* **The Problem:** The national energy regulator (**ERÚ**) publishes raw lists of technical production licenses without statutory owner names or business registration details. Manual searching for warm outreach contacts was impossible.
* **The Solution:**
  - Automated ingestion of license records and batch querying of the official Czech Ministry of Finance **ARES REST API** (`ares.gov.cz`).
  - Automated extraction of legal entities, statutory executives, registered seats, and CZ-NACE industry classifications.
  - Rate limiting, exponential backoff for HTTP 429, and export into **Airtable**-ready CSV and JSON for Make.com automation.

### 2. `modules/penb_document_extractor` — Municipal Energy Audit OCR (`Pasportizace`)
* **The Real Business Context:** Deployed for comprehensive energy audits (*pasportizace* and EnMS) across Central Bohemian municipalities (Pečky, Vitice, Křečhoř, Nová Ves I, Konojedy, etc.).
* **The Problem:** Municipal building archives consist of hundreds of legacy, poorly scanned PDF certificates (PENB - *Průkaz energetické náročnosti budovy*). Standard PDF parsers fail due to scanned image pages, missing text layers, and OCR diacritic corruptions.
* **The Solution:**
  - Hybrid extraction pipeline using **PyMuPDF (`fitz`)**, **pypdf**, and **Tesseract OCR** with custom trained models (`ces.traineddata`).
  - Robust regex grammar for Czech date declensions (genitive month names: *května*, *října*, etc.) and automated repair of OCR glue artifacts (`platnostdo`, `platnostod`).
  - Automated compliance verification: Evaluates 10-year statutory validity under Czech Decree 78/2013 Sb. and flags expired municipal certificates.

### 3. `modules/opendescript_transcription` — OpenDescript AI Media Core
* **The Real Business Context:** Core engine for **OpenDescript**, a 1,600+ line Python desktop application (PyQt6 + ffmpeg) built to allow video editing directly through text transcription.
* **The Solution:**
  - Integration with **`faster-whisper`** featuring automatic CUDA GPU acceleration with graceful fallback to CPU `int8`.
  - Voice Activity Detection (**VAD**) filtering to remove dead audio silence.
  - Word-level timestamp alignment and synchronized timeline export into interactive JSON and standard SRT formats.

### 4. `modules/web_lead_harvester` — Forum & Market Signal Harvester
* **The Solution:** Lightweight, zero-rate-penalty RSS/ATOM XML harvester monitoring market discussions across designated subreddits and business forums, extracting real-time user pain points and lead opportunities.

---

## 🚀 Running the Suite

### Prerequisites
```bash
git clone https://github.com/TVUJ_NICK/registry-lead-pipeline.git
cd registry-lead-pipeline
pip install -r requirements.txt
```

### CLI Orchestrator Usage
You can run the entire portfolio or target individual modules:

```bash
# Run all verified modules in sequence:
python pipeline.py --module all

# Run only the live ARES & Enerkom pipeline:
python pipeline.py --module ares

# Run the Municipal PENB Document Classifier:
python pipeline.py --module penb

# Run the OpenDescript Audio Transcription engine:
python pipeline.py --module media
```

---

## 📋 Data Contracts & Pipeline Schemas

### ARES Enriched Entity Schema
```json
{
  "ico": "27082440",
  "company_name": "Alza.cz a.s.",
  "legal_form": "Akciová společnost",
  "legal_form_code": 121,
  "registered_address": "Jankovcova 1522/53, Holešovice, 17000 Praha 7",
  "city": "Praha",
  "postal_code": "17000",
  "cz_nace": ["47910", "46900", "52290"],
  "is_active": true,
  "source_license_type": "FVE / Commercial Rooftop",
  "installed_capacity_kw": 480.0,
  "district": "Praha-Holešovice",
  "lookup_status": "SUCCESS"
}
```

### PENB Classification Audit Schema
```json
{
  "document_name": "PENB_ZSDruzinova_Pecky.pdf",
  "municipality": "Pečky",
  "identified_dates": ["14.05.2019", "14.05.2029"],
  "issue_date": "14.05.2019",
  "valid_until": "14.05.2029",
  "is_legally_valid": true,
  "energy_rating_class": "C",
  "status_notes": "Platnost do 14.05.2029 (PLATNÝ)."
}
```

---

## 🛠️ Tech Stack & Integrations

- **Languages & Frameworks:** Python 3.9+, PyQt6, PyMuPDF, requests, ElementTree.
- **AI & Models:** Claude Code, Cursor, faster-whisper, Tesseract OCR.
- **No-Code & Automation Tools:** Apify.com, Airtable, Make.com, GitHub Webhooks.
- **Domain Specialization:** Czech Administrative Data (ARES, ERÚ), Building Energy Passports (PENB), Multimedia Timelines.

---

## 👤 Author Contact

**Jaroslav Karbusický**  
Student of *Digitální podnikání* at Univerzita Pardubice  
- Email: `jara.karbusicky@gmail.com`  
- Phone: `+420 606 068 340`  
- Location: Cerhenice / Praha / Remote  
- LinkedIn: [linkedin.com/in/jaroslavkarbusicky](https://linkedin.com/in/jaroslavkarbusicky)
