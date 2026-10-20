from pathlib import Path
import pymupdf


def extract_pdf(pdf_path, output_path):
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    total_pages = 0
    total_chars = 0

    with pymupdf.open(pdf_path) as document:
        with output_path.open(
            "w",
            encoding="utf-8"
        ) as output:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")
                output.write(text)
                output.write("\n")

                total_pages += 1
                total_chars += len(text)

    return {
        "pages": total_pages,
        "characters": total_chars,
        "output": str(output_path)
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print(
            "Penggunaan: python extract_pdf.py "
            "input.pdf output.txt"
        )
        raise SystemExit(1)

    result = extract_pdf(sys.argv[1], sys.argv[2])
    print(result)

    if result["characters"] == 0:
        print(
            "PERINGATAN: tidak ditemukan teks. "
            "PDF mungkin memerlukan OCR."
        )
