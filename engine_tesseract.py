# ============================================================
# TESSERACT ENGINE (FINAL CLEAN + MATCH PDF/EASYOCR)
# ============================================================
import io
import time
import os
import sys
import warnings
os.environ["MallocStackLogging"] = "0"
os.environ["MallocStackLoggingNoCompact"] = "1"
warnings.filterwarnings("ignore")
sys.stderr = open(os.devnull, 'w')
import pandas as pd
import pytesseract
from contextlib import redirect_stdout
from library import (
    DEFAULT_DPI_LIST,
    convert_pdf_page_to_image,
    extract_raw_lines,
    parse_inline_lines_to_df,
    detect_income_statement_pages,
    compute_income_anchors,
    compute_income_diff,
    major_hits_from_anchors,
    coverage_from_df,
    classify_status,
    validate_buffett_inputs,
    validate_saii_inputs
)
DEBUG_MODE = True
PAGE_FINDER_DEBUG = False
RAW_TEXT_DEBUG = False

# ============================================================
# OCR
# ============================================================
def ocr_image_tesseract(image):
    return pytesseract.image_to_string(image)

# ============================================================
# PAGE DETECTION (SILENT OPTION)
# ============================================================
def get_income_candidate_pages(pdf_path, max_pages=20):
    if PAGE_FINDER_DEBUG:
        return detect_income_statement_pages(pdf_path, max_pages=max_pages)
    silent_buffer = io.StringIO()
    with redirect_stdout(silent_buffer):
        pages = detect_income_statement_pages(pdf_path, max_pages=max_pages)
    return pages

# ============================================================
# MAIN ENGINE
# ============================================================
def run_tesseract_engine(pdf_path, dpi_list=None, max_pages=20):
    dpi_list = dpi_list or DEFAULT_DPI_LIST
    start_time = time.perf_counter()
    print("\n--------------------------------------------------")
    print(f"🟢 TESSERACT ENGINE | {pdf_path.split('/')[-1]}")
    print("--------------------------------------------------")
    print("🚀 Launching tesseract_v1")
    candidate_pages = get_income_candidate_pages(pdf_path, max_pages=max_pages)
    print(f"🧭 Pages: {candidate_pages}")
    best = None
    best_score = (-1, -1, -1, -1, -1)
    # ============================================================
    # LOOP PAGES
    # ============================================================
    for page_no in candidate_pages:
        print(f"\n  📄 Page {page_no}")
        for i, dpi in enumerate(dpi_list):
            print(f"🟢 Tesseract | DPI={dpi} | Page={page_no} | 🔁 Parse | {i + 1}/{len(dpi_list)}")
            image = convert_pdf_page_to_image(pdf_path, page_number=page_no, dpi=dpi)
            if image is None:
                print(f"   🔁 DPI {dpi} → STRUCTURE_BAD | Diff=inf | Hits=0")
                continue
            text = ocr_image_tesseract(image)
            # ====================================================
            # RAW TEXT DEBUG
            # ====================================================
            if RAW_TEXT_DEBUG:
                print("\n🖼️ --- OCR TEXT PREVIEW ---")
                preview_lines = text.split("\n")[:20]
                for line in preview_lines:
                    print(line)
                print("--------------------------------")
            lines = extract_raw_lines(text)
            df = parse_inline_lines_to_df(lines)
            # ============================================================
            # 🔴 HARD FILTER — REQUIRE NUMBERS
            # ============================================================
            has_numbers = False
            if df is not None and not df.empty:
                num_cols = [c for c in df.columns if c != 'Item']
                if num_cols:
                    has_numbers = df[num_cols].notna().any().any()
            if not has_numbers:
                print("   🚫 Skipped → No numeric data")
                continue
            if df is None:
                df = pd.DataFrame()
            row_count = len(df)
            # ====================================================
            # SAFE COMPUTATION
            # ====================================================
            if df.empty:
                anchors = {}
                buffett_status = {'status': 'FAILED','missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'FinanceCost'],'missing_important': ['GrossProfitReported', 'SGA', 'PreTaxCalc']}
                saii_status = {'status': 'FAILED','missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'PreTaxCalc', 'TaxZakat', 'FinanceCost']}
                diff = float('inf')
                major_hits = 0
                coverage_percent = 0.0
                col_conf = 0
                status = 'STRUCTURE_BAD'
            else:
                anchors = compute_income_anchors(df)
                # ============================================================
                # 🔴 HARD FILTER — FAKE ZERO ANCHORS
                # ============================================================
                rev = anchors.get('Revenue')
                cost = anchors.get('CostOfSales')
                try:
                    rev_val = float(str(rev).replace(',', '')) if rev is not None else None
                    cost_val = float(str(cost).replace(',', '')) if cost is not None else None
                except:
                    rev_val = None
                    cost_val = None
                if rev_val == 0 and cost_val == 0:
                    print("   🚫 Skipped → Fake zero anchors")
                    continue
                buffett_status = validate_buffett_inputs(anchors)
                saii_status = validate_saii_inputs(anchors)
                major_hits = major_hits_from_anchors(anchors)
                coverage = coverage_from_df(df)
                coverage_percent = coverage['coverage_percent']
                # =========================
                # COLUMN CONFIDENCE (FIXED)
                # =========================
                col_count = len(df.columns)
                if col_count >= 3:
                    col_conf = 2
                elif col_count == 2:
                    col_conf = 1
                else:
                    col_conf = 0
                diff = compute_income_diff(anchors)
                status = classify_status(diff, major_hits, col_conf, coverage_percent, len(df))
                # ============================================================
                # 🔴 HARD BLOCK — INVALID DIFF SHOULD NEVER PASS
                # ============================================================
                if diff == float('inf'):
                    print("🚫 Forcing STRUCTURE_BAD due to infinite diff")
                    status = "STRUCTURE_BAD"
            # ====================================================
            # PRINT RESULT
            # ====================================================
            diff_text = 'inf' if diff == float('inf') else round(diff, 2)
            if DEBUG_MODE:
                print(f"    🔁 DPI {dpi} → Rows={row_count} | Hits={major_hits} | Diff={diff_text} → {status}")
            else:
                if status in ['SUCCESS_CONSOLIDATED', 'SUCCESS_STRUCTURE_ONLY']:
                    print(f"    ✔ DPI {dpi} → {status} | Hits={major_hits} | Diff={diff_text}")
            if DEBUG_MODE and not df.empty:
                print(df.to_string(index=False))
            # ====================================================
            # BUILD RESULT
            # ====================================================
            result = {'engine': 'tesseract','dpi': dpi,'pages_used': [page_no],'df': df,'anchors': anchors,'buffett_status': buffett_status,'saii_status': saii_status,'major_hits': major_hits,'col_conf': col_conf,'diff': diff,'status': status,'coverage': coverage_percent}
            # ====================================================
            # SCORING
            # ====================================================
            score = (3 if status == 'SUCCESS_CONSOLIDATED' else 2 if status == 'SUCCESS_STRUCTURE_ONLY' else 1, major_hits, col_conf, -diff if diff != float('inf') else -1e12, row_count)
            if score > best_score:
                best = result
                best_score = score
    # ============================================================
    # FINAL RESULT
    # ============================================================
    if best is None:
        best = {'engine': 'tesseract','dpi': None,'pages_used': [],'df': pd.DataFrame(),'anchors': {},'buffett_status': {'status': 'FAILED','missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'FinanceCost'],'missing_important': ['GrossProfitReported', 'SGA', 'PreTaxCalc']},'saii_status': {'status': 'FAILED','missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'PreTaxCalc', 'TaxZakat', 'FinanceCost']},'major_hits': 0,'col_conf': 0,'diff': float('inf'),'status': 'STRUCTURE_BAD','coverage': 0.0}
    print("\n🏁 BEST RESULT (TESSERACT)")
    print(f"   Page: {best['pages_used']} | DPI: {best['dpi']} | Status: {best['status']} | Diff: {'inf' if best['diff']==float('inf') else best['diff']} | Hits: {best['major_hits']}")
    print(f"   🧠 Buffett: {best['buffett_status']['status']} | SAII: {best['saii_status']['status']}")
    best['runtime_sec'] = time.perf_counter() - start_time
    return best