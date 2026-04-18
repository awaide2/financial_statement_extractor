# ============================================================
# EASY OCR ENGINE (FINAL CLEAN + PAGE_FINDER_DEBUG)
# ============================================================

import io
import os
import sys
import time
import re
import warnings
import numpy as np
import pandas as pd
import easyocr
from contextlib import redirect_stdout
from library import (DEFAULT_DPI_LIST, convert_pdf_page_to_image, extract_raw_lines, detect_income_statement_pages,
                     compute_income_anchors, compute_income_diff, major_hits_from_anchors, coverage_from_df,parse_inline_lines_to_df,
                     classify_status, is_number_like, is_note_like, validate_buffett_inputs, validate_saii_inputs,compute_anchor_confidence)


warnings.filterwarnings("ignore")
os.environ["MallocStackLogging"] = "0"
os.environ["MallocStackLoggingNoCompact"] = "1"
# ==== SILENCE MACOS MALLOC WARNING ====
sys.stderr = open(os.devnull, 'w')

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

DEBUG_MODE = True
PAGE_FINDER_DEBUG = False
RAW_TEXT_DEBUG = True

# NOTE: GPU=True only if available
EASYOCR_READER = easyocr.Reader(['en'], gpu=True)



# ============================================================
# 🧠 OCR DISTORTION HANDLING STRATEGY
# ============================================================
#
# We do NOT assume a fixed table structure.
# OCR converts 2D tables into noisy 1D text streams.
#
# We handle OCR distortions, not structures.
#
# Distortion types:
#
# INLINE_CLEAN:
#   Revenue   100   200 → handled by inline parser (future optional)
#
# VERTICAL:
#   Revenue
#   100
#   200
#   → handled by row-search parser
#
# VERTICAL_WITH_NOTES:
#   Revenue
#   6
#   100
#   200
#   → skip notes, use row-search
#
# DAMAGED_NUMBERS:
#   1,
#   081,783,416
#   → future: number reconstruction
#
# MULTILINES_NO_NUMBERS:
#   long labels split across lines
#   → future: label merging
#
# SHIFTED_COLUMNS:
#   Revenue     100
#                200
#   → future: column alignment parser
#
# NOISE_ROWS:
#   Chairman / CFO etc
#   → filter out
#
# PARTIAL_ROWS:
#   incomplete grouping
#
# ------------------------------------------------------------
# CURRENT APPROACH:
# - Use row-search parser (robust default)
# - Score result via anchors/diff/coverage
#
# FUTURE:
# - Add inline parser + compare
# - Add column parser
#
# IMPORTANT:
# DO NOT detect structure explicitly
# ============================================================

# ============================================================
# OCR HELPER
# ============================================================

def ocr_image_easyocr(image):
    return '\n'.join(EASYOCR_READER.readtext(np.array(image), detail=0))


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


def is_year_line(text):
    t = str(text).strip()
    return bool(re.fullmatch(r'20\d{2}', t)) or bool(re.fullmatch(r'20\d{2}\s+20\d{2}', t))

def parse_easyocr_row_search_df(lines):
    formatted = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if not re.search(r'[A-Za-z]', line):
            i += 1
            continue
        label = line
        label_l = label.lower()
        if 'year ended' in label_l or 'notes' in label_l:
            i += 1
            continue
        if len(label.strip()) < 4:
            i += 1
            continue
        nums = []
        j = i + 1
        gap = 0
        while j < len(lines):
            next_line = lines[j].strip()
            if not next_line:
                gap += 1
                if gap > 3:
                    break
                j += 1
                continue
            if is_note_like(next_line):
                j += 1
                continue
            if is_year_line(next_line):
                j += 1
                continue
            if re.search(r'[A-Za-z]', next_line) and not is_number_like(next_line):
                break
            if is_number_like(next_line):
                nums.append(next_line)
                j += 1
                if len(nums) == 2:
                    break
                continue
            gap += 1
            if gap > 3:
                break
            j += 1
        nums = nums[:2]
        if len(nums) >= 1:
            if len(nums) == 1:
                formatted.append([label, nums[0], None])
            else:
                formatted.append([label, nums[0], nums[1]])
            i = j
            continue
        i += 1
    if not formatted:
        return pd.DataFrame(columns=['Item','Year1','Year2'])
    df = pd.DataFrame(formatted, columns=['Item','Year1','Year2'])
    return df

# ============================================================
# MAIN ENGINE
# ============================================================

def run_easyocr_engine(pdf_path,dpi_list=None,max_pages=20):
    dpi_list=dpi_list or DEFAULT_DPI_LIST
    start_time=time.perf_counter()
    print("\n--------------------------------------------------")
    print(f"🔵 EASYOCR ENGINE | {pdf_path.split('/')[-1]}")
    print("--------------------------------------------------")
    print("🚀 Launching easyocr_v1")
    candidate_pages=get_income_candidate_pages(pdf_path,max_pages=max_pages)
    print(f"🧭 Pages: {candidate_pages}")
    best=None
    best_score = (-1, -1, -1, -1, -1, -1)
    for page_no in candidate_pages:
        print(f"\n📄 Page {page_no}")
        for i,dpi in enumerate(dpi_list):
            print(f"🔵 EasyOCR  | DPI={dpi} | Page={page_no} | 🔁 Parse | {i+1}/{len(dpi_list)}")
            image=convert_pdf_page_to_image(pdf_path,page_number=page_no,dpi=dpi)
            if image is None:
                print(f"   🔁 DPI {dpi} → Rows=0 | Hits=0 | Diff=inf → STRUCTURE_BAD")
                continue
            text=ocr_image_easyocr(image)
            if RAW_TEXT_DEBUG:
                print("\n🖼️ --- OCR TEXT PREVIEW ---")
                preview_lines=text.split("\n")[:20]
                for line in preview_lines:
                    print(line)
                print("--------------------------------")
            lines=extract_raw_lines(text)

            # ====================================================
            # 🔁 DUAL PARSER EXECUTION
            # ====================================================
            df_row=parse_easyocr_row_search_df(lines)
            try:
                df_inline=parse_inline_lines_to_df(lines)
            except Exception:
                df_inline=pd.DataFrame()

            # ====================================================
            # 🧠 EVALUATE BOTH PARSERS
            # ====================================================
            def evaluate_df(df):
                if df is None or df.empty:
                    return {'df': pd.DataFrame(), 'score': (-1, -1, -1, -1, -1, -1), 'anchors': {}, 'diff': float('inf'),
                            'hits': 0, 'coverage': 0.0, 'col_conf': 0, 'status': 'STRUCTURE_BAD', 'rows': 0,
                            'buffett_status': {'status': 'FAILED',
                                               'missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc',
                                                                    'FinanceCost'],
                                               'missing_important': ['GrossProfitReported', 'SGA', 'PreTaxCalc']},
                            'saii_status': {'status': 'FAILED',
                                            'missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc',
                                                                 'PreTaxCalc', 'TaxZakat', 'FinanceCost']}}
                anchors = compute_income_anchors(df)
                # ====================================================
                # 🔴 HARD VALIDATION: INVALID REVENUE DETECTION
                # ====================================================

                buffett_status = validate_buffett_inputs(anchors)
                saii_status = validate_saii_inputs(anchors)
                diff = compute_income_diff(anchors)
                hits = major_hits_from_anchors(anchors)
                coverage = coverage_from_df(df)['coverage_percent']
                col_count = len(df.columns)
                col_conf = 2 if col_count >= 3 else 1 if col_count == 2 else 0
                status = classify_status(diff, hits, col_conf, coverage, len(df))
                anchor_conf = compute_anchor_confidence(anchors)

                score = (3 if status == 'SUCCESS_CONSOLIDATED' else 2 if status == 'SUCCESS_STRUCTURE_ONLY' else 1,
                         anchor_conf, hits, col_conf, -diff if diff != float('inf') else -1e12, len(df))

                return {'df': df, 'score': score, 'anchors': anchors, 'diff': diff, 'hits': hits, 'coverage': coverage,
                        'col_conf': col_conf, 'status': status, 'rows': len(df), 'buffett_status': buffett_status,
                        'saii_status': saii_status}


            res_row=evaluate_df(df_row)
            res_inline=evaluate_df(df_inline)

            # ====================================================
            # 🏆 PICK BEST PARSER
            # ====================================================
            if res_inline['score']>res_row['score']:
                chosen=res_inline
                parser_used='INLINE'
            else:
                chosen=res_row
                parser_used='ROW_SEARCH'

            df = chosen['df']
            anchors = chosen['anchors']
            buffett_status = chosen['buffett_status']
            saii_status = chosen['saii_status']
            diff = chosen['diff']
            major_hits = chosen['hits']
            coverage_percent = chosen['coverage']
            col_conf = chosen['col_conf']
            status = chosen['status']
            row_count = chosen['rows']

            diff_text='inf' if diff==float('inf') else round(diff,2)

            print(f"    🧠 Parser Selected: {parser_used}")

            if DEBUG_MODE:
                print(f"    🔁 DPI {dpi} → Rows={row_count} | Hits={major_hits} | Diff={diff_text} → {status}")
            else:
                if status in ['SUCCESS_CONSOLIDATED','SUCCESS_STRUCTURE_ONLY']:
                    print(f"    ✔ DPI {dpi} → {status} | Hits={major_hits} | Diff={diff_text}")

            if DEBUG_MODE and not df.empty:
                print(df.to_string(index=False))

            anchor_conf = compute_anchor_confidence(anchors)
            result = {'engine': 'easyocr', 'dpi': dpi, 'pages_used': [page_no], 'df': df, 'anchors': anchors,
                      'buffett_status': buffett_status, 'saii_status': saii_status, 'major_hits': major_hits,
                      'col_conf': col_conf, 'diff': diff, 'status': status, 'coverage': coverage_percent,
                      'anchor_conf': anchor_conf}
            score = (3 if status == 'SUCCESS_CONSOLIDATED' else 2 if status == 'SUCCESS_STRUCTURE_ONLY' else 1,
                     anchor_conf, major_hits, col_conf, -diff if diff != float('inf') else -1e12, row_count)
            if score>best_score:
                best=result
                best_score=score

    if best is None:
        best = {'engine': 'easyocr', 'dpi': None, 'pages_used': [], 'df': pd.DataFrame(), 'anchors': {},
                'buffett_status': {'status': 'FAILED',
                                   'missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc',
                                                        'FinanceCost'],
                                   'missing_important': ['GrossProfitReported', 'SGA', 'PreTaxCalc']},
                'saii_status': {'status': 'FAILED',
                                'missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'PreTaxCalc',
                                                     'TaxZakat', 'FinanceCost']}, 'major_hits': 0, 'col_conf': 0,
                'diff': float('inf'), 'status': 'STRUCTURE_BAD', 'coverage': 0.0}

    print("\n🏁 BEST RESULT (EASYOCR)")
    print(f"   Page: {best['pages_used']} | DPI: {best['dpi']} | Status: {best['status']} | Diff: {'inf' if best['diff']==float('inf') else best['diff']} | Hits: {best['major_hits']}")
    print(f"   🧠 Buffett: {best['buffett_status']['status']} | SAII: {best['saii_status']['status']}")
    # ============================================================
    # 🔴 FINAL LABEL NORMALIZATION (CRITICAL FIX)
    # ============================================================
    if best.get('df') is not None and not best['df'].empty:
        best['df']['Item'] = best['df']['Item'].astype(str)
        best['df']['Item'] = best['df']['Item'].str.strip()
        best['df'].loc[best['df']['Item'].str.lower() == 'profit', 'Item'] = 'Gross profit'

    best['runtime_sec'] = time.perf_counter() - start_time
    return best
