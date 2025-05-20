def _to_float(x) -> float:
    """
    Safely convert strings like '1 600.00', '1 600,00', '1600.00' to float.
    Strips out spaces (incl. non-breaking), replaces commas with dots.
    """
    s = str(x) or "0"
    # remove NBSP and normal spaces
    s = s.replace("\xa0", "").replace(" ", "")
    # comma → dot
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0