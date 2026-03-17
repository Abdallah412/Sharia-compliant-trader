"""
Deterministic pre-screen — catches obvious cases cheaply BEFORE
spending tokens on the Sheikh Agent.
"""

KNOWN_HARAM = {
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BRK-A", "BRK-B",  # banks
    "V", "MA", "AXP", "DFS",                                    # credit
    "MO", "PM", "BTI", "LO",                                    # tobacco
    "BUD", "TAP", "STZ", "SAM",                                 # alcohol
    "LVS", "MGM", "WYNN", "CZR",                                # casinos
}

KNOWN_HALAL_ETFS = {"SPUS", "HLAL", "MNZL", "SPTE"}  # pre-screened by fund manager

HARAM_SECTORS = {"Financials"}

HARAM_INDUSTRIES = {
    "Banks—Regional", "Banks—Diversified", "Banks—Global",
    "Insurance—Life", "Insurance—Property & Casualty",
    "Credit Services", "Mortgage Finance",
    "Beverages—Wineries & Distilleries", "Beverages—Brewers",
    "Gambling", "Casinos & Gaming", "Tobacco",
}


def pre_screen(ticker: str, sector: str = "", industry: str = "") -> str | None:
    """
    Returns 'HARAM' or 'HALAL_ETF' if deterministic.
    Returns None if Sheikh Agent should be called.
    """
    ticker_upper = ticker.upper()
    if ticker_upper in KNOWN_HARAM:
        return "HARAM"
    if ticker_upper in KNOWN_HALAL_ETFS:
        return "HALAL_ETF"
    if sector in HARAM_SECTORS:
        return "HARAM"
    if industry in HARAM_INDUSTRIES:
        return "HARAM"
    return None  # needs Sheikh Agent
