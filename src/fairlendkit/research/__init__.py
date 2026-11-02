"""Research-only artifacts; not part of the product capability contract."""
from fairlendkit.research.uci_south_german_credit import (
    SouthGermanCreditBenchmark,
    load_south_german_credit,
)

__all__ = ["SouthGermanCreditBenchmark", "load_south_german_credit"]
