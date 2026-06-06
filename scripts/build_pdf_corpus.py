"""
Generate ~10 PDF documents from existing Markdown sources and append to manifest.

Run from project/: python scripts/build_pdf_corpus.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpdf import FPDF

from backend.config import DOCUMENTS_DIR

# Source MD paths (relative to documents/) -> PDF output + manifest title suffix
PDF_SOURCES = [
    ("hr/employee_handbook.md", "hr/employee_handbook.pdf", "Employee Handbook (PDF)", "HR", "public"),
    ("hr/compensation_policy.md", "hr/compensation_policy.pdf", "Compensation Policy (PDF)", "HR", "restricted"),
    ("hr/leave_policy.md", "hr/leave_policy.pdf", "Leave Policy (PDF)", "HR", "public"),
    ("engineering/incident_report_5023.md", "engineering/incident_report_5023.pdf", "Incident Report INC-5023 (PDF)", "Engineering", "public"),
    ("engineering/architecture_overview.md", "engineering/architecture_overview.pdf", "Architecture Overview (PDF)", "Engineering", "public"),
    ("engineering/on_call_runbook.md", "engineering/on_call_runbook.pdf", "On-Call Runbook (PDF)", "Engineering", "public"),
    ("sales/pricing_tiers.md", "sales/pricing_tiers.pdf", "Pricing Tiers (PDF)", "Sales", "public"),
    ("sales/quota_commission_guide.md", "sales/quota_commission_guide.pdf", "Quota and Commission Guide (PDF)", "Sales", "restricted"),
    ("sales/sales_playbook.md", "sales/sales_playbook.pdf", "Sales Playbook (PDF)", "Sales", "restricted"),
    ("sales/customer_case_study.md", "sales/customer_case_study.pdf", "Customer Case Study - BigCorp (PDF)", "Sales", "public"),
]


def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


def _safe_line(line: str) -> str:
    return line.encode("latin-1", errors="replace").decode("latin-1")


def md_to_pdf(md_path: Path, pdf_path: Path, title: str):
    raw = md_path.read_text(encoding="utf-8")
    plain = strip_markdown(raw)

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    w = pdf.w - pdf.l_margin - pdf.r_margin

    def write_para(text: str):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(w, 5, _safe_line(text))

    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    write_para(title)
    pdf.ln(2)

    chunk_size = 2500
    for i in range(0, len(plain), chunk_size):
        if i > 0:
            pdf.add_page()
        block = plain[i : i + chunk_size]
        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue
            for start in range(0, len(line), 80):
                write_para(line[start : start + 80])

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(pdf_path))


def main():
    manifest_path = DOCUMENTS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_paths = {e["path"] for e in manifest}

    added = 0
    for src_rel, pdf_rel, title, dept, classification in PDF_SOURCES:
        src = DOCUMENTS_DIR / src_rel
        pdf_out = DOCUMENTS_DIR / pdf_rel
        if not src.exists():
            print(f"  Skip missing source: {src_rel}")
            continue
        print(f"  Building {pdf_rel} ...")
        md_to_pdf(src, pdf_out, title)
        entry = {
            "path": pdf_rel.replace("\\", "/"),
            "title": title,
            "department": dept,
            "classification": classification,
            "source_id": "PDF-GEN",
        }
        if entry["path"] not in existing_paths:
            manifest.append(entry)
            existing_paths.add(entry["path"])
            added += 1
        else:
            print(f"    Already in manifest: {pdf_rel}")

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone. Added {added} PDF entries. Total manifest: {len(manifest)} documents.")


if __name__ == "__main__":
    main()
