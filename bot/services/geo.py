import math
from typing import Optional


def calculate_distance(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> float:
    """
    Haversine formulasi orqali ikkita GPS nuqta orasidagi masofani (km) hisoblaydi.
    Agar koordinatalar berilmagan bo'lsa, xavfsiz default qiymat qaytaradi.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999.0  # Noma'lum masofa

    # Radius of earth in kilometers
    r = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    distance = r * c
    return round(distance, 2)


def is_within_radius(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float], max_km: float) -> bool:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return True  # Agar aniq koordinata bo'lmasa, shahar bo'yicha ruxsat
    return calculate_distance(lat1, lon1, lat2, lon2) <= max_km
