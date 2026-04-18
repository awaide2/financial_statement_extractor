# ============================================================
# HYBRID INCOME ENGINE (FINAL CLEAN VERSION)
# ============================================================

import time
import re
import numpy as np
import pandas as pd
import math
from engine_pdf_text import run_pdf_text_engine
from engine_easyocr import run_easyocr_engine
from engine_tesseract import run_tesseract_engine
from engine_inline import run_inline_engine
from engine_vertical import run_vertical_engine
from library import result_score, fmt_num, fmt_diff_value,detect_insurance_model
from library import fuse_income_anchors, compute_income_diff, major_hits_from_anchors,select_best_structure
from labels_v3 import SUSPICIOUS_PATTERNS

DEBUG_MODE = False


# ============================================================
# HELPER: FORMAT ANCHORS (NO SCIENTIFIC NOTATION)
# ============================================================

def fmt_anchor(x):
    try:
        arr = np.array(x, dtype=float).flatten()
        arr = arr[~np.isnan(arr)]
        if len(arr) == 0:
            return 'nan'
        if len(arr) == 1:
            return fmt_num(arr[0])
        return ' | '.join([fmt_num(v) for v in arr])
    except:
        return str(x)



# ============================================================
# HELPER: FORMAT VALIDATION
# ============================================================

def fmt_check(flag):
    return "✔ OK" if flag else "✖ Mismatch"




# ============================================================
# 🔍 LABEL MATCH CHECK
# ============================================================
def match_label(item,label_patterns):
    if not item:
        return False
    item=item.lower()
    for pattern in label_patterns:
        if re.search(pattern,item):
            return True

    return False


# ============================================================
# HELPER: PRINT INCOME SUMMARY
# ============================================================

def print_income_summary(best):

    anchors = best['anchors']

    print("\n" + "=" * 40)
    print("📊 Income Summary")
    print("=" * 40)

    print(f"\nEngine      : {best['engine']}")
    print(f"Status      : {best['status']}")
    print(f"Diff        : {fmt_diff_value(best['diff'])}")
    print(f"Major Hits  : {best['major_hits']}")

    print("\n------------------------------------")
    print("🧮 Core Metrics")
    print("------------------------------------")

    print(f"Revenue        : {fmt_anchor(anchors.get('Revenue'))}")
    print(f"Cost of Sales  : {fmt_anchor(anchors.get('CostOfSales'))}")
    print(f"Gross Profit   : {fmt_anchor(anchors.get('GrossProfitReported'))} | Calc: {fmt_anchor(anchors.get('GrossProfitCalc'))}")

    print(f"\nSG&A           : {fmt_anchor(anchors.get('SGA'))}")
    print(f"Operating Calc : {fmt_anchor(anchors.get('OperatingProfitCalc'))}")

    print(f"\nPre-Tax        : {fmt_anchor(anchors.get('PreTaxReported'))} | Calc: {fmt_anchor(anchors.get('PreTaxCalc'))}")
    print(f"Tax            : {fmt_anchor(anchors.get('TaxZakat'))}")
    print(f"Net Income     : {fmt_anchor(anchors.get('NetIncomeReported'))} | Calc: {fmt_anchor(anchors.get('NetIncomeCalc'))}")

    print("\n------------------------------------")
    print("📐 Validation Checks")
    print("------------------------------------")

    def safe_compare(a, b):
        try:
            if isinstance(a, (list, tuple, np.ndarray, pd.Series)) or isinstance(b, (list, tuple, np.ndarray, pd.Series)):
                return np.allclose(np.array(a, dtype=float), np.array(b, dtype=float), equal_nan=True)
            return pd.notna(a) and pd.notna(b) and abs(a - b) <= 1
        except:
            return False

    print(f"Gross Check   : {fmt_check(safe_compare(anchors.get('GrossProfitReported'), anchors.get('GrossProfitCalc')))}")
    print(f"PreTax Check  : {fmt_check(safe_compare(anchors.get('PreTaxReported'), anchors.get('PreTaxCalc')))}")
    print(f"Net Check     : {fmt_check(safe_compare(anchors.get('NetIncomeReported'), anchors.get('NetIncomeCalc')))}")

    print("\n------------------------------------")
    print("📊 Structure Quality")
    print("------------------------------------")

    print(f"Coverage      : {best.get('coverage', 0)}%")


# ============================================================
# HELPER: SCORE DISPLAY
# ============================================================

def format_score(name, res, score):
    diff_text = fmt_diff_value(res.get('diff'))
    return f"{name:<10} • {res.get('status')} | Score={score[1]} | Hits={score[2]} | Cols={score[3]} | Diff={diff_text} | Rows={score[5]}"
# ============================================================
# MAIN HYBRID FUNCTION
# ============================================================

# ============================================================
# HELPER: STRONG ANCHOR VALIDATION
# ============================================================
def has_strong_anchor_quality(res):
    anchors = res.get('anchors') or {}
    revenue = anchors.get('Revenue')
    cost = anchors.get('CostOfSales')
    gross_rep = anchors.get('GrossProfitReported')
    gross_calc = anchors.get('GrossProfitCalc')
    pretax = anchors.get('PreTaxReported')
    net_income = anchors.get('NetIncomeReported')
    def to_clean_array(v):
        try:
            arr = np.array(v, dtype=float).flatten()
            arr = arr[~np.isnan(arr)]
            return arr
        except:
            return np.array([], dtype=float)
    revenue_arr = to_clean_array(revenue)
    cost_arr = to_clean_array(cost)
    gross_rep_arr = to_clean_array(gross_rep)
    gross_calc_arr = to_clean_array(gross_calc)
    pretax_arr = to_clean_array(pretax)
    net_income_arr = to_clean_array(net_income)
    if revenue_arr.size == 0 or net_income_arr.size == 0:
        return False
    if np.nanmean(revenue_arr) <= 0:
        return False
    if cost_arr.size > 0 and np.nanmean(cost_arr) > 0:
        return False
    if gross_rep_arr.size > 0 and gross_calc_arr.size > 0:
        gross_diff = np.nansum(np.abs(gross_rep_arr - gross_calc_arr))
        if math.isfinite(gross_diff) and gross_diff > 1000:
            return False
    if pretax_arr.size > 0 and revenue_arr.size > 0:
        if np.nanmax(np.abs(pretax_arr)) > np.nanmax(np.abs(revenue_arr)):
            return False
    return True



def fix_anchors_with_fallback(best_anchors,all_engine_anchors):
    print("🔵 Running anchor fallback correction...")
    def is_valid(anchor,vals):
        if vals is None:
            return False
        try:
            arr=np.array(vals,dtype=float).flatten()
            arr=arr[~np.isnan(arr)]
            if arr.size==0:
                return False
            v0=arr[0]
            if anchor=="Revenue":
                return v0>0
            if anchor in ["CostOfSales","SGA","FinanceCost","TaxZakat"]:
                return v0<0
            return True
        except:
            return False
    def score(anchor,vals):
        try:
            arr=np.array(vals,dtype=float).flatten()
            arr=arr[~np.isnan(arr)]
            if arr.size==0:
                return -10
            v0=arr[0]
            s=0
            if anchor=="Revenue" and v0>0:
                s+=3
            if anchor in ["CostOfSales","SGA","FinanceCost","TaxZakat"] and v0<0:
                s+=3
            if abs(v0)>0:
                s+=1
            if arr.size>=2:
                s+=1
            return s
        except:
            return -10
    corrected=dict(best_anchors) if best_anchors else {}
    print("🛡️ Validating Revenue & Cost...")
    try:
        rev=corrected.get("Revenue")
        rev_arr=np.array(rev,dtype=float).flatten()
        rev_arr=rev_arr[~np.isnan(rev_arr)]
        if rev_arr.size>0 and rev_arr[0]<=0:
            print("🔴 Invalid Revenue detected → fixing...")
            for eng_name,eng_anchors in all_engine_anchors.items():
                v=eng_anchors.get("Revenue")
                if v is None:
                    continue
                arr=np.array(v,dtype=float).flatten()
                arr=arr[~np.isnan(arr)]
                if arr.size>0 and arr[0]>0:
                    corrected["Revenue"]=v
                    print(f"🟢 Fixed Revenue from {eng_name} → {v}")
                    break
    except:
        pass
    try:
        cost=corrected.get("CostOfSales")
        cost_arr=np.array(cost,dtype=float).flatten()
        cost_arr=cost_arr[~np.isnan(cost_arr)]
        if cost_arr.size>0 and cost_arr[0]>0:
            print("🔴 Invalid Cost detected → fixing...")
            for eng_name,eng_anchors in all_engine_anchors.items():
                v=eng_anchors.get("CostOfSales")
                if v is None:
                    continue
                arr=np.array(v,dtype=float).flatten()
                arr=arr[~np.isnan(arr)]
                if arr.size>0 and arr[0]<0:
                    corrected["CostOfSales"]=v
                    print(f"🟢 Fixed Cost from {eng_name} → {v}")
                    break
    except:
        pass
    for anchor in list(corrected.keys()):
        current_vals=corrected.get(anchor)
        if anchor=="OperatingProfitCalc":
            # ============================================================
            # 🔵 FIX: USE BETTER OPERATING CANDIDATE IF AVAILABLE
            # ============================================================
            try:
                op_arr = np.array(current_vals, dtype=float).flatten()
                op_arr = op_arr[~np.isnan(op_arr)]
                if op_arr.size > 0:
                    for eng_name, eng_anchors in all_engine_anchors.items():
                        alt = eng_anchors.get("OperatingProfitCalc")
                        if alt is None:
                            continue
                        alt_arr = np.array(alt, dtype=float).flatten()
                        alt_arr = alt_arr[~np.isnan(alt_arr)]
                        if alt_arr.size > 0:
                            # 🔴 choose larger magnitude (real operating is usually bigger)
                            if abs(alt_arr[0]) > abs(op_arr[0]) * 2 and abs(alt_arr[0]) < 1e12:
                                corrected["OperatingProfitCalc"] = alt
                                print(f"🟢 Improved OperatingProfit from {eng_name}")
                                break
            except:
                pass
            
            op_val=current_vals
            other_val=corrected.get("OperatingOtherIncome")
            if op_val is not None and other_val is not None:
                try:
                    op_arr=np.array(op_val,dtype=float).flatten()
                    other_arr=np.array(other_val,dtype=float).flatten()
                    op_arr=op_arr[~np.isnan(op_arr)]
                    other_arr=other_arr[~np.isnan(other_arr)]
                    if op_arr.size>0 and other_arr.size>0:
                        if abs(op_arr[0])==abs(other_arr[0]):
                            print("🔴 OperatingProfit == OtherIncome → fixing...")
                            best_candidate=None
                            best_score=-999
                            best_engine=None
                            for eng_name,eng_anchors in all_engine_anchors.items():
                                vals=eng_anchors.get(anchor)
                                if vals is None:
                                    continue
                                try:
                                    vals_arr=np.array(vals,dtype=float).flatten()
                                    vals_arr=vals_arr[~np.isnan(vals_arr)]
                                    other_candidate=eng_anchors.get("OperatingOtherIncome")
                                    other_arr2=np.array(other_candidate,dtype=float).flatten()
                                    other_arr2=other_arr2[~np.isnan(other_arr2)]
                                    if vals_arr.size>0 and other_arr2.size>0:
                                        if abs(vals_arr[0])==abs(other_arr2[0]):
                                            continue
                                except:
                                    pass
                                sc=score(anchor,vals)
                                if sc>best_score:
                                    best_score=sc
                                    best_candidate=vals
                                    best_engine=eng_name
                            if best_candidate is not None:
                                corrected[anchor]=best_candidate
                                print(f"🟢 Fixed OperatingProfit from {best_engine}")
                                continue
                except:
                    pass
        if anchor=="FinanceCost":
            fc_val=current_vals
            ref_val=corrected.get("PreTaxReported")
            if fc_val is not None and ref_val is not None:
                try:
                    fc_arr=np.array(fc_val,dtype=float).flatten()
                    ref_arr=np.array(ref_val,dtype=float).flatten()
                    fc_arr=fc_arr[~np.isnan(fc_arr)]
                    ref_arr=ref_arr[~np.isnan(ref_arr)]
                    if fc_arr.size>0 and ref_arr.size>0:
                        if abs(fc_arr[0])>abs(ref_arr[0])*2:
                            print("🔴 FinanceCost too large → fixing...")
                            best_candidate=None
                            best_score=-999
                            for eng_name,eng_anchors in all_engine_anchors.items():
                                vals=eng_anchors.get(anchor)
                                if vals is None:
                                    continue
                                sc=score(anchor,vals)
                                if sc>best_score:
                                    best_score=sc
                                    best_candidate=vals
                            if best_candidate is not None:
                                corrected[anchor]=best_candidate
                                print("🟢 Fixed FinanceCost")
                                continue
                except:
                    pass
        if is_valid(anchor,current_vals):
            continue
        print(f"🟡 Fixing anchor → {anchor}")
        best_candidate=None
        best_score=-999
        for eng_name,eng_anchors in all_engine_anchors.items():
            vals=eng_anchors.get(anchor)
            if not is_valid(anchor,vals):
                continue
            sc=score(anchor,vals)
            if sc>best_score:
                best_score=sc
                best_candidate=vals
        if best_candidate is not None:
            corrected[anchor]=best_candidate
            print(f"🟢 Replaced {anchor}")
        else:
            print(f"🟤 No valid replacement for {anchor}")
    print("🔍 Final consistency check...")
    try:
        pretax=corrected.get("PreTaxCalc")
        net=corrected.get("NetIncomeCalc")
        pretax_arr=np.array(pretax,dtype=float).flatten()
        net_arr=np.array(net,dtype=float).flatten()
        pretax_arr=pretax_arr[~np.isnan(pretax_arr)]
        net_arr=net_arr[~np.isnan(net_arr)]
        if net_arr.size>0 and pretax_arr.size>0:
            if net_arr[0]>pretax_arr[0]:
                print("🔴 Net > PreTax → fixing...")
                for eng_name,eng_anchors in all_engine_anchors.items():
                    v=eng_anchors.get("NetIncomeCalc")
                    p=eng_anchors.get("PreTaxCalc")
                    try:
                        v_arr=np.array(v,dtype=float).flatten()
                        p_arr=np.array(p,dtype=float).flatten()
                        v_arr=v_arr[~np.isnan(v_arr)]
                        p_arr=p_arr[~np.isnan(p_arr)]
                        if v_arr.size>0 and p_arr.size>0:
                            if v_arr[0]<=p_arr[0]:
                                corrected["NetIncomeCalc"]=v
                                print(f"🟢 Fixed NetIncome from {eng_name}")
                                break
                    except:
                        pass
    except:
        pass
    print("🟢 Anchor correction done")
    return corrected


def run_hybrid_engine(pdf_path, dpi_list_easy=None, dpi_list_tess=None, max_pages=20):

    start_time = time.perf_counter()

    print("==================================================")
    print(f"📄 Processing File: {pdf_path.split('/')[-1]}")
    print("==================================================")

    print("==============================")
    print("🧠 Hybrid Engine Start")
    print("==============================")

    # ------------------------------------------------------------
    # RUN ENGINES
    # ------------------------------------------------------------

    pdf_result = run_pdf_text_engine(pdf_path)
    inline_pages = pdf_result.get('pages_used')

    if not inline_pages:
        inline_pages = [1]  # fallback only if nothing else

    inline_result = run_inline_engine(pdf_path, inline_pages[0])
    vertical_result = run_vertical_engine(pdf_path)
    tess_result = run_tesseract_engine(pdf_path, dpi_list_tess)
    easy_result = run_easyocr_engine(pdf_path, dpi_list_easy)

    total_time = time.perf_counter() - start_time

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------

    print("\n==================================================")
    print("⏱ Runtime Snapshot")
    print("==================================================")

    print(f"PDF     : {pdf_path}")
    print(f"Runtime : {round(total_time, 2)} sec")

    # ------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------

    pdf_score = result_score(pdf_result)
    easy_score = result_score(easy_result)
    tess_score = result_score(tess_result)
    inline_score = result_score(inline_result)
    vertical_score = result_score(vertical_result)

    print("\n==============================")
    print("📊 Scores")
    print("==============================")

    print(format_score("PDF_TEXT", pdf_result, pdf_score))
    print(format_score("INLINE", inline_result, inline_score))
    print(format_score("VERTICAL", vertical_result, vertical_score))
    print(format_score("Tesseract", tess_result, tess_score))
    print(format_score("EasyOCR", easy_result, easy_score))
    # ------------------------------------------------------------
    # FINAL DECISION
    # ------------------------------------------------------------
    all_results = [pdf_result, inline_result, vertical_result, tess_result, easy_result]
    valid_results = [r for r in all_results if r.get("status") != "STRUCTURE_BAD"]
    # ============================================================
    # 🧠 FILTER OUT FAKE RESULTS (ZERO ANCHORS)
    # ============================================================
    filtered_results = []
    for r in valid_results:
        anchors = r.get("anchors") or {}
        try:
            rev = np.array(anchors.get("Revenue"), dtype=float).flatten()
            rev = rev[~np.isnan(rev)]
            cost = np.array(anchors.get("CostOfSales"), dtype=float).flatten()
            cost = cost[~np.isnan(cost)]
            # 🔴 HARD RULES (prevents OCR corruption)
            if rev.size > 0 and rev[0] < 0:
                continue
            if cost.size > 0 and cost[0] > 0:
                continue
        except:
            continue
        if has_strong_anchor_quality(r):
            filtered_results.append(r)

    if filtered_results:
        print(f"🟢 Filter kept {len(filtered_results)}/{len(valid_results)} engines")
        valid_results = filtered_results
    else:
        print("🔴 Filter removed ALL engines → reverting to original results")
    # ============================================================
    # 🛡 CRITICAL FALLBACK (PREVENT CRASH)
    # ============================================================
    if not valid_results:
        print("\n⚠️ All engines returned STRUCTURE_BAD → fallback to best available")

        # fallback to ALL results (even bad ones)
        valid_results = all_results

    # ============================================================
    # 🔥 FALLBACK TO FUSION IF ALL STRUCTURE_BAD
    # ============================================================
    all_bad = all(r.get("status") == "STRUCTURE_BAD" for r in all_results)

    if all_bad:
        print("\n⚠️ All engines returned STRUCTURE_BAD → using fusion result")
        fused_anchors = fuse_income_anchors(all_results)
        fused_diff = compute_income_diff(fused_anchors)
        fused_hits = major_hits_from_anchors(fused_anchors)
        print(f"\n🧠 Fusion Result → diff={fused_diff} | hits={fused_hits}")
        # ============================================================
        # 🧠 GLOBAL STRUCTURE SELECTION (NEW)
        # ============================================================
        engine_results = {
            "pdf_text": pdf_result,
            "inline": inline_result,
            "vertical": vertical_result,
            "tesseract": tess_result,
            "easyocr": easy_result
        }

        selected_df, selected_source = select_best_structure(engine_results)
        if selected_df is not None:
            print(f"🟢 Using DF from: {selected_source} | rows={len(selected_df)}")
        else:
            print("⚠️ No valid DF found in structure selection")
            selected_df = easy_result.get("df") if easy_result.get("df") is not None and not easy_result.get(
                "df").empty else None
            if selected_df is not None:
                print(f"🔵 Fallback DF → EasyOCR | rows={len(selected_df)}")
        return {
            "engine": "FUSION",
            "status": "SUCCESS_STRUCTURE_ONLY",
            "diff": fused_diff,
            "major_hits": fused_hits,
            "anchors": fused_anchors,
            "df": selected_df,  # 🔥 SAFE
            "pdf_result": pdf_result,
            "easy_result": easy_result,
            "tess_result": tess_result,
            "inline_result": inline_result,
            "vertical_result": vertical_result
        }

    # ============================================================
    # 🏆 SELECT BEST (NOW SAFE)
    # ============================================================
    best = max(valid_results, key=lambda x: result_score(x))
    # ============================================================
    # 🧠 APPLY FUSION (IF BEST IS WEAK)
    # ============================================================

    if best.get("status") != "SUCCESS_CONSOLIDATED":
        fused = fuse_income_anchors(valid_results)
        if fused:
            fused_diff = compute_income_diff(fused)
            fused_hits = major_hits_from_anchors(fused)
            print(f"\n🧠 Fusion Result → diff={fused_diff} | hits={fused_hits}")
            # ------------------------------------------------------------
            # accept only if better
            # ------------------------------------------------------------
            if fused_hits > best.get("major_hits", 0):
                print("🟢 Fusion selected (better anchors)")
                best['anchors'] = fused
                best['diff'] = fused_diff
                best['major_hits'] = fused_hits
                best['engine'] = "FUSION"

    print("\n==============================")
    print("🧠 Final Decision")
    print("==============================")

    print(f"🏆 Selected Engine : {best['engine']}")
    print(f"Status            : {best['status']}")
    print(f"Diff              : {fmt_diff_value(best['diff'])}")
    print(f"Hits              : {best['major_hits']}")
    print(f"Page              : {best.get('pages_used')}")

    print("\n📌 Reason")
    print("  - Best score")
    print("  - Best reconciliation")
    print("  - Highest anchor quality")

    # ------------------------------------------------------------
    # ANCHORS
    # ------------------------------------------------------------
    if best.get("status") != "STRUCTURE_BAD":
        anchors = best.get('anchors')
        if anchors is None:
            from library import compute_income_anchors
            anchors = compute_income_anchors(best.get('df'))
            best['anchors'] = anchors
        is_insurance = False
        try:
            if best.get("df") is not None and not best.get("df").empty:
                is_insurance = detect_insurance_model(best.get("df"))
        except:
            is_insurance = False
        print(f"🟦 Insurance Model Detected: {is_insurance}")
        if is_insurance:
            try:
                op_candidate = anchors.get("OperatingProfitCalc")
                other_income = anchors.get("OperatingOtherIncome")
                pretax_candidate = anchors.get("PreTaxReported")
                finance_candidate = anchors.get("FinanceCost")
                op_arr = np.array(op_candidate, dtype=float).flatten()
                op_arr = op_arr[~np.isnan(op_arr)]
                other_arr = np.array(other_income, dtype=float).flatten()
                other_arr = other_arr[~np.isnan(other_arr)]
                pretax_arr = np.array(pretax_candidate, dtype=float).flatten()
                pretax_arr = pretax_arr[~np.isnan(pretax_arr)]
                finance_arr = np.array(finance_candidate, dtype=float).flatten()
                finance_arr = finance_arr[~np.isnan(finance_arr)]
                if op_arr.size > 0 and other_arr.size > 0 and abs(op_arr[0]) == abs(
                        other_arr[0]) and pretax_arr.size > 0 and abs(pretax_arr[0]) > abs(op_arr[0]):
                    print("🟦 Insurance override → OperatingProfitCalc from PreTaxReported")
                    anchors["OperatingProfitCalc"] = anchors.get("PreTaxReported")
                if finance_arr.size > 0 and pretax_arr.size > 0 and abs(finance_arr[0]) > abs(pretax_arr[0]) * 2:
                    print("🟦 Insurance override → clearing suspicious FinanceCost")
                    anchors["FinanceCost"] = np.array([np.nan])
            except:
                pass
        all_engine_anchors = {
            "pdf_text": pdf_result.get("anchors", {}) or {},
            "inline": inline_result.get("anchors", {}) or {},
            "vertical": vertical_result.get("anchors", {}) or {},
            "tesseract": tess_result.get("anchors", {}) or {},
            "easyocr": easy_result.get("anchors", {}) or {}
        }
        anchors = fix_anchors_with_fallback(anchors, all_engine_anchors)
        best['anchors'] = anchors
    else:
        anchors = {}

    print("\n🔎 Key Anchors")
    print(f"  Revenue : {fmt_anchor(anchors.get('Revenue'))}")
    print(f"  Cost    : {fmt_anchor(anchors.get('CostOfSales'))}")
    print(f"  Gross   : {fmt_anchor(anchors.get('GrossProfitReported'))}")
    print(f"  Op      : {fmt_anchor(anchors.get('OperatingProfitCalc'))}")
    print(f"  PreTax  : {fmt_anchor(anchors.get('PreTaxReported'))}")
    print(f"  Net     : {fmt_anchor(anchors.get('NetIncomeReported'))}")

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    print_income_summary(best)

    # ------------------------------------------------------------
    # ENGINE COMPARISON (MOVED TO END)
    # ------------------------------------------------------------

    print("\n==============================")
    print("⚖ Engine Comparison")
    print("==============================")

    for name, res in [
        ("PDF_TEXT", pdf_result),
        ("INLINE", inline_result),
        ("VERTICAL", vertical_result),
        ("Tesseract", tess_result),
        ("EasyOCR", easy_result)
    ]:

        print(f"{name:<10} • {res.get('status')} | Diff={fmt_diff_value(res.get('diff'))} | Hits={res.get('major_hits')}")

    # ------------------------------------------------------------
    # FINAL TABLE
    # ------------------------------------------------------------

    print("\n------------------------------------")
    print("📄 Final Table (Top 10 rows)")
    print("------------------------------------")

    if best.get('df') is not None and not best['df'].empty:
        print(best['df'].head(10))
    else:
        print("⚠ No final DataFrame to display")
    best['pdf_result'] = pdf_result
    best['easy_result'] = easy_result
    best['tess_result'] = tess_result
    best['inline_result'] = inline_result
    best['vertical_result'] = vertical_result

    return best