"""Pacote de scraping do fminside-scraper (FMInside → Gofoot Studio)."""

from fminside.models import Jogador
from fminside.pipeline import ScrapeFilters, run_scrape

__all__ = ["Jogador", "ScrapeFilters", "run_scrape"]
