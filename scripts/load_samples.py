from pathlib import Path


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_judgments"


def main() -> None:
    SAMPLE_DIR.mkdir(exist_ok=True)
    pdfs = sorted(SAMPLE_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(
            "No sample PDFs found. Place 10 real Karnataka High Court judgment PDFs in "
            f"{SAMPLE_DIR} before running this loader."
        )
    print(f"Found {len(pdfs)} sample judgment PDF(s):")
    for pdf in pdfs:
        print(f"- {pdf.name}")
    print("Upload these through POST /api/v1/judgments/upload or the frontend Upload screen.")


if __name__ == "__main__":
    main()
