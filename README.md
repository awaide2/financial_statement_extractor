# Financial Statement Extraction System

## 📌 Overview
This project aims to build a robust, scalable system to extract financial statements from PDF reports using a multi-engine approach.

The system is designed to handle different formats, layouts, and OCR challenges while maintaining high accuracy and validation integrity.

---

## 🎯 Objectives

The system will extract:

- Income Statement  
- Balance Sheet  
- Cash Flow Statement  

---

## 🚀 Final Goals

- Full structured extraction from PDFs  
- Consolidation of key financial items (Revenue, Cost, Net Income, etc.)  
- Automatic validation (financial reconciliation)  
- Support for Buffett-style metrics  
- Support for SAII risk and ratio calculations  
- Excel output for human audit and verification  

---

## 🧠 Architecture (High Level)

Batch Runner  
    ↓  
Hybrid Engine (selection + scoring)  
    ↓  
Multiple Extraction Engines  
    ↓  
Shared Library (anchors, validation, scoring)  
    ↓  
Labels & Rules  
    ↓  
Output (Excel + Debug)  

---

## ⚙️ Key Components

### 1. Batch Runner
Runs extraction across multiple PDFs and tracks results.

### 2. Hybrid Engine
Selects the best result from multiple engines based on:
- Accuracy (diff)
- Coverage
- Structural integrity

### 3. Extraction Engines
Includes:
- OCR-based engines (EasyOCR, Tesseract)
- Structure-based parsers
- Specialized format handlers

### 4. Shared Library
Handles:
- Anchor detection
- Financial validation
- Scoring logic

### 5. Labels System
Defines financial terms and mapping rules for consistent extraction.

---

## 🧪 Validation Rules

- Income statement must reconcile (Revenue → Net Income)
- Balance sheet must satisfy:
  Assets = Liabilities + Equity
- Outputs are classified as:
  - SUCCESS_CONSOLIDATED
  - SUCCESS_STRUCTURE_ONLY
  - FAIL

---

## 📂 Project Structure

src/  
  income_statement/  
  balance_sheet/  
  cashflow/  
  shared/  

configs/  
  labels/  

tests/  
  regression/  

outputs/  
  excel/  
  debug/  

agents/  

---

## 🔒 Design Principles

- Do not break working logic  
- Extend engines instead of replacing them  
- Use versioned parsers (parser_v1, parser_v2, ...)  
- Always validate results before accepting changes  
- Avoid hardcoding company-specific patterns  

---

## 📊 Current Status

- Initial repository setup complete  
- Base architecture defined  
- Ready for integration of existing income statement engines  

---

## 🔜 Next Steps

- Integrate current income statement extraction engines  
- Build regression testing framework  
- Improve hybrid engine scoring  
- Expand parser coverage  
- Add balance sheet extraction  

---

## 🧩 Long-Term Vision

A fully automated financial extraction and analysis engine capable of:

- Handling multiple PDF formats  
- Producing audit-ready structured data  
- Feeding advanced financial models (Buffett / SAII)  
