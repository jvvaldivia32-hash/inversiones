# Universo fijo del Radar (~90 tickers) — sección 3.2 del plan madre. Snapshot tomado a
# mano el 2026-08-13, no se actualiza solo: la composición del S&P 100 cambia de vez en
# cuando, revisar cada tanto (no cada semana — la lista de miembros no se mueve tan rápido).
#
# Los ETFs de referencia (VOO/QQQ/VTI) NO van acá — van a "Referencias" (sección 3.2, nota
# del plan), no son candidatos de inversión individual.

GRANDES_CONOCIDAS = {
    "MSFT": "Microsoft",
    "TSLA": "Tesla",
    "JNJ": "Johnson & Johnson",
    "V": "Visa",
    "MA": "Mastercard",
    "PG": "Procter & Gamble",
    "HD": "Home Depot",
    "MRK": "Merck",
    "ABBV": "AbbVie",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "LLY": "Eli Lilly",
    "PEP": "PepsiCo",
    "KO": "Coca-Cola",
    "COST": "Costco",
    "WMT": "Walmart",
    "ADBE": "Adobe",
    "CSCO": "Cisco",
    "TMO": "Thermo Fisher Scientific",
    "ABT": "Abbott Laboratories",
    "ACN": "Accenture",
    "DHR": "Danaher",
    "VZ": "Verizon",
    "CMCSA": "Comcast",
    "NKE": "Nike",
    "TXN": "Texas Instruments",
    "NEE": "NextEra Energy",
    "PM": "Philip Morris International",
    "UNH": "UnitedHealth Group",
    "DIS": "Walt Disney",
    "WFC": "Wells Fargo",
    "UPS": "United Parcel Service",
    "RTX": "RTX Corporation",
    "HON": "Honeywell",
    "QCOM": "Qualcomm",
    "IBM": "IBM",
    "GE": "GE Aerospace",
    "CAT": "Caterpillar",
    "BA": "Boeing",
    "SBUX": "Starbucks",
    "LOW": "Lowe's",
    "SPGI": "S&P Global",
    "PYPL": "PayPal",
    "AMGN": "Amgen",
    "GILD": "Gilead Sciences",
    "MDT": "Medtronic",
    "BLK": "BlackRock",
    "AXP": "American Express",
    "ISRG": "Intuitive Surgical",
    "NOW": "ServiceNow",
}

ADRS_CHILENOS = {
    "BCH": "Banco de Chile",
    "BSAC": "Banco Santander Chile",
    "SQM": "Sociedad Química y Minera de Chile",
    "ENIC": "Enel Chile",
    "CCU": "Compañía Cervecerías Unidas",
    "LTM": "LATAM Airlines Group",
}

SECTORES_INTERES = {
    # Gaming
    "EA": "Electronic Arts",
    "TTWO": "Take-Two Interactive",
    "RBLX": "Roblox",
    "NTDOY": "Nintendo (ADR)",
    "UBSFY": "Ubisoft (ADR)",
    "SONY": "Sony Group (ADR)",
    # Autos / JDM
    "TM": "Toyota Motor (ADR)",
    "HMC": "Honda Motor (ADR)",
    "F": "Ford Motor",
    "GM": "General Motors",
    "STLA": "Stellantis",
    "RACE": "Ferrari",
    # Tech
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "NVDA": "NVIDIA",
    "META": "Meta Platforms",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    # Bancos
    "JPM": "JPMorgan Chase",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
}

UNIVERSO: dict[str, str] = {**GRANDES_CONOCIDAS, **ADRS_CHILENOS, **SECTORES_INTERES}
