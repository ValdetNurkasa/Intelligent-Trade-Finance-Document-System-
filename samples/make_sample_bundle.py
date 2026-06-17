"""
Generate born-digital and scanned trade bundle PDFs for pipeline testing.

Usage:
    python samples/make_sample_bundle.py --out tests/bundles/clean_01
    python samples/make_sample_bundle.py --out tests/bundles/scanned_01 --scanned
    python samples/make_sample_bundle.py --out tests/bundles/tolerance_03 --scenario tolerance
"""
from __future__ import annotations
import argparse
import io
import random
from pathlib import Path

import fitz  # PyMuPDF
import yaml


# ─── Document content templates ───────────────────────────────────────────────

def _lc_text(scenario: str) -> str:
    amount = "250,000.00" if scenario != "tolerance" else "250,000.00"
    return f"""\
DOCUMENTARY LETTER OF CREDIT
Documentary Credit No: LC-2026-00099
Date of Issue: 01/06/2026
Applicant: Adriatic Imports Sh.p.k.
Address: Rr. Nene Tereza 12, Prishtina, Kosovo
Beneficiary: Shenzhen Lition Electronics Co Ltd
Address: Bao'an District, Shenzhen, China
Amount: USD {amount}
Currency: USD
Expiry Date: 2026-07-31
Latest Date of Shipment: 2026-07-10
Presentation Period: within 21 days
Port of Loading: Shenzhen
Port of Discharge: Durres
Partial Shipments: NOT ALLOWED
Transhipment: NOT ALLOWED
Goods: Electronic Components - PCB Assemblies
"""


def _invoice_text(scenario: str) -> str:
    if scenario == "tolerance":
        amount = "250,750.00"   # 0.3 % over LC (passes 5 % default tolerance)
    elif scenario == "bl_late":
        amount = "250,000.00"
    else:
        amount = "250,000.00"
    beneficiary = "Shenzhen Lition Electronics Co Ltd"
    if scenario == "name_variation":
        beneficiary = "Shenzhen Lition Electronics Company Ltd"
    return f"""\
COMMERCIAL INVOICE
Invoice No: INV-2026-0099
Invoice Date: 10/06/2026
Seller / Beneficiary: {beneficiary}
Address: Bao'an District, Shenzhen, China
Buyer / Applicant: Adriatic Imports Sh.p.k.
Address: Rr. Nene Tereza 12, Prishtina, Kosovo
Port of Loading: Shenzhen
Port of Discharge: Durres
Incoterms: CIF Durres
Description of Goods: Electronic Components - PCB Assemblies
Quantity: 5,000 PCS
Unit Price: USD 50.00
Total Amount: USD {amount}
Currency: USD
Documentary Credit No: LC-2026-00099
"""


def _bol_text(scenario: str) -> str:
    onboard = "05/07/2026" if scenario == "bl_late" else "05/06/2026"
    return f"""\
BILL OF LADING
BL No: COSU2026060501
Vessel: MV Adriatic Star
Voyage No: V-208E
Shipper: Shenzhen Lition Electronics Co Ltd
Consignee: Adriatic Imports Sh.p.k.
Notify Party: Adriatic Imports Sh.p.k.
Port of Loading: Shenzhen
Port of Discharge: Durres
Shipped on Board Date: {onboard}
Description of Goods: Electronic Components - PCB Assemblies
Gross Weight: 12,500 KGS
Measurement: 45 CBM
Freight: FREIGHT PREPAID
"""


def _packing_list_text() -> str:
    return """\
PACKING LIST
Packing List No: PL-2026-0099
Date: 10/06/2026
Exporter: Shenzhen Lition Electronics Co Ltd
Importer: Adriatic Imports Sh.p.k.
Description of Goods: Electronic Components - PCB Assemblies
Total Packages: 250 Cartons
Gross Weight: 12,500 KGS
Net Weight: 11,800 KGS
Total Quantity: 5,000 PCS
"""


def _cert_origin_text() -> str:
    return """\
CERTIFICATE OF ORIGIN
Certificate No: COO-2026-0099
Date: 10/06/2026
Exporter: Shenzhen Lition Electronics Co Ltd
Country of Origin: China
Description of Goods: Electronic Components - PCB Assemblies
Quantity: 5,000 PCS
Gross Weight: 12,500 KGS
"""


# ─── PDF builders ─────────────────────────────────────────────────────────────

def _make_pdf_born_digital(text: str) -> bytes:
    """Create a text-based (born-digital) PDF and return raw bytes."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_text((50, 60), text, fontname="helv", fontsize=10)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pdf_scanned(text: str, noise_level: int = 15) -> bytes:
    """
    Simulate a scanned page:
    1. Render a born-digital PDF to image.
    2. Add Gaussian noise + slight rotation with PIL.
    3. Save back as an image-only PDF (no text layer).
    """
    from PIL import Image, ImageFilter
    import numpy as np

    born_digital_bytes = _make_pdf_born_digital(text)
    doc = fitz.open(stream=born_digital_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(2.0, 2.0)   # 144 dpi
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    # Add noise
    rng = np.array(img, dtype=np.int16)
    noise = np.random.normal(0, noise_level, rng.shape).astype(np.int16)
    noisy = np.clip(rng + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy)

    # Slight blur (simulates defocus)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    # Slight rotation
    angle = random.uniform(-1.0, 1.0)
    img = img.rotate(angle, fillcolor=(255, 255, 255))

    # Save as image-only PDF
    img_buf = io.BytesIO()
    img.save(img_buf, format="PDF")
    return img_buf.getvalue()


# ─── Bundle builder ───────────────────────────────────────────────────────────

DOCS = [
    ("lc.pdf",             _lc_text),
    ("invoice.pdf",        _invoice_text),
    ("bill_of_lading.pdf", _bol_text),
    ("packing_list.pdf",   lambda _: _packing_list_text()),
    ("cert_origin.pdf",    lambda _: _cert_origin_text()),
]


def build_bundle(out_dir: Path, scenario: str = "clean", scanned: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    make_pdf = _make_pdf_scanned if scanned else _make_pdf_born_digital

    for filename, text_fn in DOCS:
        pdf_bytes = make_pdf(text_fn(scenario))
        (out_dir / filename).write_bytes(pdf_bytes)

    manifest = {
        "bundle_id": out_dir.name,
        "lc_number": "LC-2026-00099",
        "currency": "USD",
        "amount": 250000.00,
        "expiry_date": "2026-07-31",
        "latest_shipment_date": "2026-07-10",
        "presentation_period_days": 21,
        "incoterms": "CIF",
        "ucp_version": "UCP600",
        "applicant": {"name": "Adriatic Imports Sh.p.k.", "address": "Prishtina, Kosovo", "country": "XK"},
        "beneficiary": {"name": "Shenzhen Lition Electronics Co Ltd", "address": "Shenzhen, China", "country": "CN"},
        "issuing_bank": {"name": "Banka Kombetare Tregtare", "address": "Prishtina, Kosovo", "swift": "NCBAXKPRXXX", "country": "XK"},
        "advising_bank": {"name": "Bank of China", "address": "Shenzhen, China", "swift": "BKCHCNBJ45A", "country": "CN"},
        "vessel": {"name": "MV Adriatic Star", "imo": "9123456", "flag_state": "Panama", "voyage": "V-208E"},
        "ports": {"loading": "Shenzhen", "discharge": "Durres"},
        "flags": {
            "partial_shipment_allowed": False,
            "transhipment_allowed": False,
            "tolerance_percent": 5.0,
        },
        "documents": [
            {"type": "letter_of_credit",       "file": "lc.pdf"},
            {"type": "commercial_invoice",      "file": "invoice.pdf"},
            {"type": "bill_of_lading",          "file": "bill_of_lading.pdf"},
            {"type": "packing_list",            "file": "packing_list.pdf"},
            {"type": "certificate_of_origin",   "file": "cert_origin.pdf"},
        ],
        "scenario": scenario,
        "scanned": scanned,
        "expected_outcome": {
            "clean": "HONOUR",
            "tolerance": "HONOUR",
            "bl_late": "REFER",
            "name_variation": "HONOUR",
        }.get(scenario, "UNKNOWN"),
        "notes": {
            "clean": "All documents consistent, no discrepancies.",
            "tolerance": "Invoice 0.3% over LC amount — within 5% tolerance, should honour.",
            "bl_late": "B/L on-board date after latest shipment date — major discrepancy.",
            "name_variation": "Beneficiary name differs slightly (Co vs Company) — fuzzy match should succeed.",
        }.get(scenario, ""),
    }
    with open(out_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)

    bundle_type = "scanned" if scanned else "born-digital"
    print(f"[make_sample_bundle] {bundle_type} bundle '{scenario}' -> {out_dir}")
    for f in sorted(out_dir.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size:,} bytes)")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a trade bundle for testing.")
    parser.add_argument("--out", required=True, help="Output directory path")
    parser.add_argument("--scenario", default="clean",
                        choices=["clean", "tolerance", "bl_late", "name_variation"],
                        help="Which discrepancy scenario to generate")
    parser.add_argument("--scanned", action="store_true",
                        help="Generate scanned (image-only) PDFs instead of born-digital")
    args = parser.parse_args()

    build_bundle(Path(args.out), scenario=args.scenario, scanned=args.scanned)


if __name__ == "__main__":
    main()
