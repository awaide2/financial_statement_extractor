# ======================================
# INCOME STATEMENT LABELS (ENHANCED - STAGE G READY)
# ======================================

INCOME_HEADER_PATTERNS = [
    r'statement of profit or loss',
    r'consolidated statement of profit or loss',
    r'consolidated statement of income',
    r'statement of income',
    r'income statement',
    r'statement of earnings',
    r'results of operations'
]

# =========================
# REQUIRED (for coverage)
# =========================
required_income_labels = [
    'revenue',
    'gross profit',
    'operating profit',
    'profit before',
    'net profit'
]

# =========================
# REVENUE
# =========================
revenue_labels = [
    'revenue','revenues','sales','total revenue','net sales',
    'contract revenue','turnover',
    'revenue from contracts with customers','insurance revenue',
    'operating revenue','total operating revenue','revenue net'
]

revenue_patterns = [
    r'^(?:total )?(?:revenue|revenues|sales|net sales|turnover)$',
    r'^revenue from',
    r'^revenues?$',
    r'^insurance revenue$',
    r'operating revenue',
    r'total operating revenue'
]

# =========================
# COST OF SALES
# =========================
cost_of_sales_labels = [
    'cost of revenue','cost of revenues','cost of sales','cost of goods sold',
    'cost of contracts','cost of services','insurance service expenses',
    'cost of operations','operating costs'
]

cost_of_sales_patterns = [
    r'cost of (?:revenue|revenues|sales|goods sold|contracts|services|operations)',
    r'^costs? of sales$',
    r'^insurance service expenses$',
    r'operating costs'
]

# =========================
# GROSS PROFIT
# =========================
gross_profit_labels = [
    'gross profit','gross income','gross loss',
    'net insurance service result','gross margin'
]

gross_profit_patterns = [
    r'^gross (?:profit|income|loss|margin)$',
    r'^net insurance service result$'
]

# =========================
# SG&A
# =========================
sga_labels = [
    'selling and distribution expenses','selling expenses','distribution expenses',
    'general and administrative expenses','general and administration expenses',
    'administrative expenses','selling, general and administrative expenses',
    'selling and marketing expenses','marketing expenses','other operating expenses'
]

sga_patterns = [
    r'selling.*distribution',
    r'general and administrative',
    r'general and administration',
    r'selling,? general and administrative',
    r'selling and marketing',
    r'administrative',
    r'marketing',
    r'^other operating expenses?$'
]

# =========================
# OTHER OPERATING
# =========================
operating_other_income_labels = [
    'other operating income','other income','income from operations',
    'gain on bargain purchase','other income, net'
]

operating_other_income_patterns = [
    r'other operating income',
    r'^other income$',
    r'^other income, net$',
    r'gain on bargain purchase',
    r'income from operations'
]

operating_other_expense_labels = [
    'other operating expenses','other expenses','impairment loss',
    'expected credit loss','expected credit loss (allowance) reversal',
    'loss on receivables','research and development expenses',
    'provision for impairment loss of trade receivables'
]

operating_other_expense_patterns = [
    r'other operating expenses',
    r'^other expenses$',
    r'impairment loss',
    r'expected credit loss',
    r'loss on receivables',
    r'research and development expenses',
    r'provision for impairment loss of trade receivables'
]

# =========================
# OPERATING PROFIT
# =========================
operating_profit_labels = [
    'operating profit','operating income','profit from operations',
    'profit from operation','operating loss',
    'operating result','results from operations'
]

operating_profit_patterns = [
    r'operating (?:profit|income|loss|result)',
    r'profit from operations?',
    r'results? from operations',
    r'^profit from operation$'
]

# =========================
# FINANCE
# =========================
finance_income_labels = [
    'finance income','financial income','interest income','investment income'
]

finance_income_patterns = [
    r'finance income',
    r'financial income',
    r'interest income',
    r'investment income'
]

finance_cost_labels = [
    'finance costs','finance cost','finance costs, net','financial charges',
    'interest expense','finance expense','borrowing costs','finance charges'
]

finance_cost_patterns = [
    r'^finance costs?$',
    r'^finance costs, net$',
    r'^finance charges$',
    r'financial charges',
    r'interest expense',
    r'finance expense',
    r'borrowing costs'
]

# =========================
# ASSOCIATES
# =========================
associate_labels = [
    'share of results of associates','share of profit of associates',
    'share of loss of associates','share of results of joint ventures',
    'equity accounted investees'
]

associate_patterns = [
    r'share of .*associates',
    r'share of .*joint ventures',
    r'equity accounted investees'
]

# =========================
# PRE-TAX
# =========================
pretax_labels = [
    'profit before zakat and income tax',
    'profit before zakat and tax',
    'profit before tax',
    'income before tax',
    'loss before tax',
    'profit before zakat',
    'net profit before zakat',
    'profit before income tax and zakat',
    'total income for the year attributable to shareholders before zakat',
    'income before zakat',
]

pretax_patterns = [
    r'^profit before (?:income tax and zakat|zakat and income tax|tax|zakat)$',
    r'profit before income tax and zakat',
    r'income before tax',
    r'loss before tax',
    r'net profit before zakat',
    r'profit before zakat',
    r'total income .* before zakat',
    r'income before zakat'
]

# =========================
# TAX
# =========================
tax_labels = [
    'income tax and zakat','zakat','zakat and income tax','income tax',
    'income tax expense','tax expense','deferred tax','withholding tax'
]

tax_patterns = [
    r'^income tax and zakat$',
    r'^zakat and income tax$',
    r'^income tax expense$',
    r'^income tax$',
    r'^tax expense$',
    r'^zakat$'
]

# =========================
# NET INCOME
# =========================
net_income_labels = [
    'net profit','net income','profit for the year','profit for the period',
    'profit attributable','net earnings','net loss','loss for the year',
    '(loss) / income attributed to shareholders before zakat and income tax',
    'profit for the year attributable to shareholders',
    'total net income','net profit for the year','net income for the year'
]

net_income_patterns = [
    r'^profit for the period$',
    r'^profit for the year$',
    r'^net (?:profit|income|loss)$',
    r'^loss for the year$',
    r'net income for the year',
    r'net profit for the year'
]

# =========================
# COMPREHENSIVE
# =========================
comprehensive_income_labels = [
    'total comprehensive income',
    'comprehensive income for the year',
    'total comprehensive (loss) / income for the year'
]

comprehensive_income_patterns = [
    r'total comprehensive income',
    r'comprehensive income for the year',
    r'total comprehensive .* income for the year'
]

# ============================================================
# 🏦 BANKING LABELS
# ============================================================
bank_revenue_labels = [
    'net special commission income',
    'net interest income',
    'total operating income'
]

bank_revenue_patterns = [
    r'net.*commission income',
    r'net.*interest income',
    r'total operating income'
]

bank_operating_profit_labels = [
    'income from operations, net',
    'operating income',
    'net insurance and investment result',
    'insurance service result'
]

bank_operating_profit_patterns = [
    r'income from operations',
    r'operating income',
    r'net insurance and investment result',
    r'insurance service result$'
]

# ============================================================
# 🏦 BANK DETECTION
# ============================================================
bank_detection_labels = [
    'special commission income',
    'net special commission income',
    'interest income'
]

bank_detection_patterns = [
    r'special commission income',
    r'net.*commission income',
    r'interest income'
]

# ============================================================
# 🔴 NEW: STRUCTURE IGNORE PATTERNS (USED IN ENGINE SCORING)
# ============================================================
STRUCTURE_IGNORE_PATTERNS = [
    r'statement of',
    r'for the year ended',
    r'notes to',
    r'accounting policies'
]


# ============================================================
# 🟡 STAGE G – SUSPICIOUS DETECTION LABELS
# ============================================================

SUSPICIOUS_PATTERNS = {
    "OperatingProfit_like_other_income": [
        r"other\s+operating\s+income",
        r"other\s+income"
    ],

    "OperatingProfit_true": [
        r"operating\s+profit",
        r"income\s+from\s+operations",
        r"profit\s+from\s+operations"
    ],

    "FinanceCost_true": [
        r"finance\s+cost",
        r"finance\s+expense",
        r"interest\s+expense",
        r"net\s+insurance\s+finance\s+expenses"
    ]
}