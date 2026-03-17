"""
Tests for backend.shariah_screener — Shariah compliance screening logic.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.shariah_screener import ShariahScreener, ScreenResult, BLACKLIST


@pytest.fixture
def screener():
    """Create a ShariahScreener with no cache side effects."""
    with patch.object(ShariahScreener, "_load_cache", return_value={}), \
         patch.object(ShariahScreener, "_save_cache"):
        return ShariahScreener()


# ---------------------------------------------------------------------------
# 1. Blacklisted tickers
# ---------------------------------------------------------------------------
class TestBlacklist:
    @pytest.mark.parametrize("ticker", ["JPM", "BAC", "WFC"])
    def test_blacklisted_ticker_is_haram(self, screener, ticker):
        """JPM, BAC, WFC are on the blacklist and must return compliant=False."""
        result = screener.screen(ticker)
        assert result.compliant is False
        assert any("blacklist" in r.lower() for r in result.fail_reasons)


# ---------------------------------------------------------------------------
# 2. Known ETF screening (SPUS — SP Funds S&P 500 Sharia Industry Exclusions ETF)
# ---------------------------------------------------------------------------
class TestETFScreening:
    @patch("backend.shariah_screener.yf")
    def test_known_etf_screening(self, mock_yf, screener):
        """SPUS should return a ScreenResult (not crash)."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "SP Funds S&P 500 Sharia Industry Exclusions ETF",
            "sector": "Financial Services",
            "industry": "Exchange Traded Fund",
            "marketCap": 500_000_000,
            "totalDebt": 0,
            "totalCash": 10_000_000,
            "shortTermInvestments": 0,
            "totalStockholderEquity": 500_000_000,
            "netReceivables": 5_000_000,
            "totalAssets": 500_000_000,
            "interestExpense": 0,
            "totalRevenue": 10_000_000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = screener.screen("SPUS")
        assert isinstance(result, ScreenResult)
        assert result.ticker == "SPUS"


# ---------------------------------------------------------------------------
# 3. ScreenResult has required fields
# ---------------------------------------------------------------------------
class TestScreenResultFields:
    def test_screen_result_has_required_fields(self):
        """ScreenResult should expose all expected fields."""
        result = ScreenResult(ticker="TEST")
        required_fields = [
            "ticker", "company_name", "sector", "industry", "compliant",
            "fail_reasons", "warnings", "debt_ratio", "cash_ratio",
            "receivables_ratio", "purification_pct", "source", "madhab_notes",
        ]
        result_dict = result.to_dict()
        for field in required_fields:
            assert field in result_dict, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# 4. Haram industry detection
# ---------------------------------------------------------------------------
class TestHaramIndustry:
    @patch("backend.shariah_screener.yf")
    def test_haram_industry_detected(self, mock_yf, screener):
        """A stock in a banking industry should be flagged HARAM."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Haram Bank Corp",
            "sector": "Financial Services",
            "industry": "Banks—Diversified",
            "marketCap": 1_000_000_000,
            "totalDebt": 100_000_000,
            "totalCash": 50_000_000,
            "shortTermInvestments": 0,
            "totalStockholderEquity": 500_000_000,
            "netReceivables": 10_000_000,
            "totalAssets": 1_000_000_000,
            "interestExpense": 50_000_000,
            "totalRevenue": 200_000_000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = screener.screen("FAKEBK")
        assert result.compliant is False
        assert any("haram" in r.lower() for r in result.fail_reasons)


# ---------------------------------------------------------------------------
# 5. Debt ratio over threshold
# ---------------------------------------------------------------------------
class TestDebtRatio:
    @patch("backend.shariah_screener.yf")
    def test_debt_ratio_over_threshold(self, mock_yf, screener):
        """Debt > 30% of market cap should be flagged HARAM."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Heavy Debt Inc",
            "sector": "Technology",
            "industry": "Software—Application",
            "marketCap": 1_000_000_000,
            "totalDebt": 400_000_000,  # 40% — above 30% threshold
            "totalCash": 10_000_000,
            "shortTermInvestments": 0,
            "totalStockholderEquity": 500_000_000,
            "netReceivables": 10_000_000,
            "totalAssets": 1_000_000_000,
            "interestExpense": 20_000_000,
            "totalRevenue": 500_000_000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = screener.screen("HVYDT")
        assert result.compliant is False
        assert result.debt_ratio is not None
        assert result.debt_ratio > 0.30
        assert any("debt" in r.lower() for r in result.fail_reasons)


# ---------------------------------------------------------------------------
# 6. Compliant stock
# ---------------------------------------------------------------------------
class TestCompliantStock:
    @patch("backend.shariah_screener.yf")
    def test_compliant_stock(self, mock_yf, screener):
        """A stock with good ratios and halal industry should be HALAL."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Clean Tech Co",
            "sector": "Technology",
            "industry": "Software—Application",
            "marketCap": 10_000_000_000,
            "totalDebt": 500_000_000,        # 5% debt ratio
            "totalCash": 200_000_000,
            "shortTermInvestments": 0,
            "totalStockholderEquity": 5_000_000_000,
            "netReceivables": 100_000_000,
            "totalAssets": 10_000_000_000,
            "interestExpense": 10_000_000,
            "totalRevenue": 2_000_000_000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = screener.screen("CLEAN")
        assert result.compliant is True
        assert len(result.fail_reasons) == 0


# ---------------------------------------------------------------------------
# 7. Purification calculation
# ---------------------------------------------------------------------------
class TestPurification:
    @patch("backend.shariah_screener.yf")
    def test_purification_calculation(self, mock_yf, screener):
        """Purification % = interestExpense / totalRevenue * 100.
        Donation = dividendAmount * purification_pct / 100."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Partial Interest Co",
            "sector": "Technology",
            "industry": "Software—Application",
            "marketCap": 10_000_000_000,
            "totalDebt": 500_000_000,
            "totalCash": 200_000_000,
            "shortTermInvestments": 0,
            "totalStockholderEquity": 5_000_000_000,
            "netReceivables": 100_000_000,
            "totalAssets": 10_000_000_000,
            "interestExpense": 100_000_000,   # 5% of revenue
            "totalRevenue": 2_000_000_000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = screener.screen("PURI")
        expected_pct = 100_000_000 / 2_000_000_000 * 100  # 5.0
        assert result.purification_pct == pytest.approx(expected_pct, abs=0.01)

        # Test the calculate_purification helper
        dividend = 1000.0
        donation = screener.calculate_purification("PURI", dividend)
        assert donation == pytest.approx(dividend * expected_pct / 100, abs=0.01)


# ---------------------------------------------------------------------------
# 8. Batch screening
# ---------------------------------------------------------------------------
class TestPortfolioScreening:
    def test_screen_portfolio(self, screener):
        """screen_portfolio should return one ScreenResult per ticker."""
        # Use blacklisted tickers to avoid network calls
        tickers = ["JPM", "BAC", "WFC"]
        results = screener.screen_portfolio(tickers)
        assert len(results) == len(tickers)
        assert all(isinstance(r, ScreenResult) for r in results)
        assert all(r.compliant is False for r in results)
