import os
import sys
import time
import pandas as pd
import logging
from hybrid_engine import run_hybrid_engine
from library import build_income_excel, build_batch_summary_excel , save_debug_case




# used to avoid warnings
os.environ['MallocStackLogging'] = '0'
os.environ["MallocStackLoggingNoCompact"] = "1"
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)

# ==== SILENCE MACOS MALLOC WARNING ====
sys.stderr = open(os.devnull, 'w')

def run_batch(folder_path='.', dpi_list_easy=None, dpi_list_tess=None, max_pages=20):
    print('\n====================================')
    print(f'INCOME HYBRID BATCH RUN -> Folder: {folder_path}')
    print('====================================')
    pdf_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')])
    if not pdf_files:
        print('No PDF files found.')
        return pd.DataFrame()
    results = []
    total_files = len(pdf_files)
    for idx, pdf in enumerate(pdf_files, start=1):
        pdf_path = os.path.join(folder_path, pdf)
        percent = idx * 100 / total_files
        print('------------------------------------')
        print(f'Processing ({idx}/{total_files}) | {percent:.1f}% | {pdf}')
        print('------------------------------------')
        start_time = time.perf_counter()
        final = run_hybrid_engine(pdf_path, dpi_list_easy=dpi_list_easy, dpi_list_tess=dpi_list_tess, max_pages=max_pages)
        runtime = time.perf_counter() - start_time
        final['runtime_sec'] = runtime
        debug_path = save_debug_case(
            pdf_path,
            final.get('pdf_result'),
            final.get('easy_result'),
            final.get('tess_result'),
            final.get('inline_result'),
            final,
            f"Runtime: {round(runtime, 2)} sec"
        )

        print(f"Debug saved: {debug_path}")
        final['runtime_sec'] = runtime
        excel_path = build_income_excel(final, pdf_path)
        print(f'Excel audit saved: {excel_path}')
        df = final.get('df')
        if df is not None and not df.empty:
            print('\nFINAL SELECTED INCOME STATEMENT')
            print('--------------------------------------------------')
            print(df.to_string(index=False))
        print(f'Completed in {runtime:.2f} seconds')
        results.append({'PDF': pdf, 'SelectedEngine': final.get('engine'), 'Status': final.get('status'), 'Diff': final.get('diff'), 'MajorHits': final.get('major_hits'), 'ColConf': final.get('col_conf'), 'DPI': final.get('dpi'), 'PagesUsed': ', '.join(map(str, final.get('pages_used') or [])), 'RuntimeSec': round(runtime, 2)})
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        print('\n====================================')
        print('BATCH SUMMARY')
        print('====================================')
        print(df_results.to_string(index=False))
        summary_path = build_batch_summary_excel(results, folder_path)
        print(f'Summary Excel saved: {summary_path}')
    return df_results

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(BASE_DIR, "statements")

    run_batch(folder_path=folder_path, dpi_list_easy=[320,300,280], dpi_list_tess=[320,300,280], max_pages=20)
