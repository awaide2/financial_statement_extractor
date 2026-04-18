import os
import io
from contextlib import redirect_stdout
import re
import math
import pandas as pd
import pytesseract
from library import convert_pdf_page_to_image, extract_raw_lines, is_number_like, is_note_like, clean_statement_df, detect_income_statement_pages, compute_income_anchors, compute_income_diff, major_hits_from_anchors, coverage_from_df, classify_status, build_engine_result, result_score, validate_buffett_inputs, validate_saii_inputs
DEBUG_MODE = False
PAGE_FINDER_DEBUG = False
RAW_TEXT_DEBUG = False

def parse_vertical_lines_to_df(lines):
    formatted = []
    i = 0
    numeric_zone = find_numeric_zone(lines)
    col_count = detect_year_column_count(lines)
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if re.search(r'[A-Za-z]', line):
            label = line
            k = i + 1
            # 🔥 merge multiline labels
            while k < len(lines):
                next_line = lines[k].strip()
                if not next_line:
                    break
                if is_number_like(next_line):
                    break
                if is_year_line(next_line):
                    break
                if is_note_like(next_line):
                    break
                if len(next_line) < 60 and not re.search(r'^\d+$', next_line):
                    label = label + ' ' + next_line
                    k += 1
                    continue
                break
            label_l = label.lower()
            # 🔥 skip noise labels
            if 'year ended' in label_l or 'notes' in label_l:
                i = k
                continue
            if len(label.strip()) < 4:
                i = k
                continue
            nums = []
            j = k
            gap = 0
            while j < len(lines) and len(nums) < col_count:
                next_line = lines[j].strip()
                if is_note_like(next_line):
                    j += 1
                    continue
                if is_year_line(next_line):
                    j += 1
                    continue
                if is_number_like(next_line):
                    nums.append(next_line)
                    gap = 0
                    j += 1
                    continue
                gap += 1
                if gap > 3:
                    break
                j += 1
            # 🔥 numeric zone fallback (alignment recovery)
            if len(nums) < col_count and numeric_zone:
                label_pos = i
                zone_start = numeric_zone[0]
                offset = label_pos - (zone_start - len(numeric_zone))
                if offset >= 0 and offset < len(numeric_zone):
                    idx = numeric_zone[offset]
                    vals = []
                    if idx < len(lines) and is_number_like(lines[idx]) and not is_year_line(lines[idx]):
                        vals.append(lines[idx])
                    if col_count == 2 and idx + 1 < len(lines) and is_number_like(lines[idx + 1]) and not is_year_line(lines[idx + 1]):
                        vals.append(lines[idx + 1])
                    if vals:
                        if len(vals) == 1:
                            nums = [vals[0], None]
                        else:
                            nums = vals
            # 🔥 final append
            if len(nums) >= 1 and any(c.isalpha() for c in label):
                if col_count == 1:
                    formatted.append([label, nums[0], None])
                else:
                    if len(nums) == 1:
                        formatted.append([label, nums[0], None])
                    else:
                        formatted.append([label, nums[0], nums[1]])
                i = j
                continue
        i += 1
    if not formatted:
        return pd.DataFrame(columns = ['Item', 'Year1', 'Year2'])
    df = pd.DataFrame(formatted, columns = ['Item', 'Year1', 'Year2'])
    df = clean_statement_df(df)
    return df

def find_numeric_zone(lines):
    numeric_positions = []
    for i in range(len(lines)):
        if is_number_like(lines[i]):
            numeric_positions.append(i)
    # group consecutive numeric lines
    groups = []
    current = []
    for idx in numeric_positions:
        if not current:
            current = [idx]
        elif idx - current[-1] <= 1:
            current.append(idx)
        else:
            groups.append(current)
            current = [idx]
    if current:
        groups.append(current)
    # select group with most numbers
    best_group = max(groups, key = lambda g: len(g)) if groups else []
    return best_group



def detect_year_column_count(lines):
    numeric_lines = []
    for line in lines:
        if is_number_like(line):
            numeric_lines.append(line)
    two_col_hits = 0
    one_col_hits = 0
    for val in numeric_lines:
        if ',' in val or '(' in val or ')' in val:
            two_col_hits += 1
        else:
            one_col_hits += 1
    if two_col_hits >= 3:
        return 2
    return 1

def is_year_line(text):
    t = text.strip()
    return bool(re.fullmatch(r'20\d{2}', t)) or bool(re.fullmatch(r'20\d{2}\s+20\d{2}', t))


def run_vertical_engine(pdf_path, dpi_list = None, max_pages = 20):
    print("\n" + "=" * 50)
    print(f"🟤 VERTICAL ENGINE | {os.path.basename(pdf_path)}")
    print("=" * 50)
    dpi_list = dpi_list if dpi_list else [320, 300, 280]
    if PAGE_FINDER_DEBUG:
        pages = detect_income_statement_pages(pdf_path, max_pages=max_pages)
    else:
        silent_buffer = io.StringIO()
        with redirect_stdout(silent_buffer):
            pages = detect_income_statement_pages(pdf_path, max_pages=max_pages)
    print(f"🧭 Pages: {pages}")
    best_result = None
    for page in pages:
        print(f"\n📄 Page {page}")
        for idx, dpi in enumerate(dpi_list, start = 1):
            if DEBUG_MODE:
                print(f"🟤 Vertical | DPI={dpi} | Page={page} | 🔁 Parse | {idx}/{len(dpi_list)}")
            image = convert_pdf_page_to_image(pdf_path, page_number = page, dpi = dpi)
            if image is None:
                print("   ❌ Image conversion failed")
                continue
            text = pytesseract.image_to_string(image)
            if RAW_TEXT_DEBUG:
                print("\n🖼️ --- OCR TEXT PREVIEW ---")
                print(text[:800])
                print("--------------------------------")
            lines = extract_raw_lines(text)
            df = parse_vertical_lines_to_df(lines)
            row_count = len(df)
            if df is None or df.empty:
                print(f"    🔁 DPI {dpi} → Rows=0 | Hits=0 | Diff=inf → STRUCTURE_BAD")
                continue
            anchors = compute_income_anchors(df)
            buffett_status = validate_buffett_inputs(anchors)
            saii_status = validate_saii_inputs(anchors)
            diff = compute_income_diff(anchors)
            hits = major_hits_from_anchors(anchors)
            col_conf = 1 if df.shape[1] >= 2 else 0
            coverage_percent = coverage_from_df(df)['coverage_percent']
            status = classify_status(diff, hits, col_conf, coverage_percent, row_count)
            diff_text = 'inf' if diff == float('inf') else round(diff, 2)
            if DEBUG_MODE or status in ['SUCCESS_CONSOLIDATED', 'SUCCESS_STRUCTURE_ONLY']:
                print(f"    🔁 DPI {dpi} → Rows={row_count} | Hits={hits} | Diff={diff_text} → {status}")
            if DEBUG_MODE:
                try:
                    print(df.head(10).to_string(index = False))
                except Exception:
                    pass
            result = build_engine_result(engine = "vertical", status = status, diff = diff, major_hits = hits, coverage = coverage_percent, anchors = anchors, df = df, col_conf = col_conf, pages_used = [page], dpi = dpi)
            # ============================================================
            # 🧠 ADD VALIDATION (SAFE INJECTION)
            # ============================================================
            result['buffett_status'] = buffett_status
            result['saii_status'] = saii_status
            if best_result is None or result_score(result) > result_score(best_result):
                best_result = result
    if best_result is None:
        print("[VERTICAL] ❌ No valid result")
        fallback = build_engine_result(engine="vertical", status="STRUCTURE_BAD", diff=float("inf"), major_hits=0,
                                       coverage=0, anchors={}, df=pd.DataFrame(), col_conf=0, pages_used=[], dpi=None)
        fallback['buffett_status'] = {'status': 'FAILED',
                                      'missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'FinanceCost'],
                                      'missing_important': ['GrossProfitReported', 'SGA', 'PreTaxCalc']}
        fallback['saii_status'] = {'status': 'FAILED','missing_required': ['Revenue', 'OperatingProfitCalc', 'NetIncomeCalc', 'PreTaxCalc',
                                                        'TaxZakat', 'FinanceCost']}
        return fallback
    print("\n🏁 BEST RESULT (VERTICAL)")
    print(f"   Page: {best_result.get('pages_used')} | DPI: {best_result.get('dpi')} | Status: {best_result.get('status')} | Diff: {best_result.get('diff')} | Hits: {best_result.get('major_hits')}")
    print(f"   🧠 Buffett: {best_result.get('buffett_status', {}).get('status')} | SAII: {best_result.get('saii_status', {}).get('status')}")
    return best_result