{\rtf1\ansi\ansicpg1252\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # Financial Statement Extraction System \'96 Claude Instructions\
\
## \uc0\u55356 \u57263  Objective\
Build a robust multi-engine system to extract:\
- Income Statement\
- Balance Sheet\
- Cashflow\
\
Final goal:\
- Full structured extraction\
- Consolidated key items (Revenue, Cost, Net Income, etc.)\
- Validation (diff = 0)\
- Buffett metrics\
- SAII ratios\
- Excel audit output\
\
---\
\
## \uc0\u55358 \u56800  System Architecture (DO NOT BREAK)\
\
Pipeline:\
\
Batch Runner  \
\uc0\u8594  Hybrid Engine  \
\uc0\u8594  Multiple Extraction Engines  \
\uc0\u8594  Shared Library (anchors, validation, scoring)  \
\uc0\u8594  Labels / Rules  \
\uc0\u8594  Output (Excel + Debug)\
\
---\
\
## \uc0\u9881 \u65039  Core Principles\
\
1. DO NOT break working logic\
2. DO NOT replace engines \'97 extend them\
3. Always prefer:\
   - adding new parser versions (parser_v2, parser_v3)\
   - instead of modifying parser_v1\
4. All changes must pass regression tests\
5. If a change improves one statement but breaks others \uc0\u8594  reject\
\
---\
\
## \uc0\u55358 \u56809  Engine Strategy\
\
System uses multiple engines:\
\
- OCR engines (EasyOCR, Tesseract)\
- Structural parsers (horizontal, vertical, multiline)\
- Label-based extraction\
- Anchor-based validation\
\
Hybrid engine selects best result based on:\
- diff (must be 0 ideally)\
- major hits\
- column confidence\
- completeness\
\
---\
\
## \uc0\u55358 \u56817  Parser Philosophy\
\
parser_v1:\
- Early proof-of-concept\
- May only work for specific formats\
- MUST NOT be deleted\
\
New parsers:\
- parser_v2, parser_v3...\
- Must expand coverage\
- Must not degrade old working cases\
\
---\
\
## \uc0\u55357 \u56522  Validation Rules\
\
Always validate:\
\
- Revenue - Cost = Gross Profit\
- Full income reconciliation\
- Balance sheet equation:\
  Assets = Liabilities + Equity\
\
If validation fails:\
\uc0\u8594  mark as STRUCTURE_ONLY or FAIL\
\
---\
\
## \uc0\u55357 \u56513  Code Organization Rules\
\
- OCR logic \uc0\u8594  /shared/ocr/\
- PDF extraction \uc0\u8594  /shared/pdf/\
- Parsing \uc0\u8594  /income_statement/engines/\
- Labels \uc0\u8594  /configs/labels/\
- Validation \uc0\u8594  /shared/validation/\
\
Do NOT mix:\
- OCR + parsing + validation in one file\
\
---\
\
## \uc0\u55358 \u56810  Testing Rules\
\
Every change must:\
\
1. Run on benchmark PDFs\
2. Run on random previous PDFs\
3. Compare:\
   - Status (CONSOLIDATED / STRUCTURE_ONLY)\
   - Diff\
   - Major hits\
\
Never assume success without testing\
\
---\
\
## \uc0\u55357 \u56520  Output Requirements\
\
Always produce:\
\
- Structured DataFrame\
- Excel output\
- Debug logs\
\
Excel must allow human verification\
\
---\
\
## \uc0\u55357 \u57003  Forbidden Actions\
\
- Deleting working parsers\
- Hardcoding company-specific logic\
- Hardcoding years (2023/2022)\
- Ignoring regression impact\
- Overfitting to one PDF\
\
---\
\
## \uc0\u55357 \u56960  Expected Behavior\
\
Claude should:\
\
- Improve robustness incrementally\
- Add new engines when needed\
- Refactor safely (modular)\
- Always validate before accepting results\
- Think in terms of systems, not scripts\
\
---\
\
## \uc0\u55357 \u56524  Long-Term Goal\
\
Unified financial engine that supports:\
\
- All statement types\
- Multi-format PDFs\
- Automated audit + ratios\
- Minimal manual correction\
\
---}