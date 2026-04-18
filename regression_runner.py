import os
import pandas as pd
import time

from hybrid_engine import run_hybrid_engine

# ================================
# CONFIG
# ================================
STATEMENTS_FOLDER = "statements"

# ================================
# RUN SINGLE FILE
# ================================
def run_single(pdf_path):
    try:
        start = time.time()

        result = run_hybrid_engine(pdf_path)

        runtime = round(time.time() - start, 2)

        return {
            "PDF": os.path.basename(pdf_path),
            "SelectedEngine": result.get("engine"),
            "Status": result.get("status"),
            "Diff": result.get("diff"),
            "MajorHits": result.get("major_hits"),
            "RuntimeSec": runtime
        }

    except Exception as e:
        return {
            "PDF": os.path.basename(pdf_path),
            "SelectedEngine": None,
            "Status": "ERROR",
            "Diff": None,
            "MajorHits": None,
            "RuntimeSec": None,
            "Notes": str(e)
        }

# ================================
# MAIN RUNNER
# ================================
def run_regression():
    files = [f for f in os.listdir(STATEMENTS_FOLDER) if f.endswith(".pdf")]

    results = []

    print("\n====================================")
    print("🔁 REGRESSION RUN STARTED")
    print("====================================\n")

    for i, file in enumerate(files, 1):
        pdf_path = os.path.join(STATEMENTS_FOLDER, file)

        print(f"\n------------------------------------")
        print(f"Processing ({i}/{len(files)}) → {file}")
        print("------------------------------------")

        result = run_single(pdf_path)
        results.append(result)

    df = pd.DataFrame(results)

    print("\n====================================")
    print("📊 REGRESSION SUMMARY")
    print("====================================\n")

    print(df)

    # Save results
    os.makedirs("outputs", exist_ok=True)
    df.to_csv("outputs/regression_results.csv", index=False)

    print("\nSaved to outputs/regression_results.csv")

    return df


if __name__ == "__main__":
    run_regression()