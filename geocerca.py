"""Utilidades de geocerca: punto-en-polígono, grids GPS y conversión de zoom."""
import math


def haversine_m(lat1, lng1, lat2, lng2):
    """Distancia en metros entre dos coordenadas."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi   = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def point_in_polygon(lat, lng, coords):
    """Ray-casting: coords es lista de [lng, lat] (orden GeoJSON)."""
    inside = False
    j = len(coords) - 1
    for i, (xi, yi) in enumerate(coords):
        xj, yj = coords[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _radius_to_zoom(radius_m: float) -> int:
    """Convierte el radio de búsqueda (m) a nivel de zoom de Google Maps."""
    if radius_m < 250:    return 17
    if radius_m < 600:    return 16
    if radius_m < 1_200:  return 15
    if radius_m < 2_500:  return 14
    if radius_m < 6_000:  return 13
    if radius_m < 12_000: return 12
    return 11


def generate_grid_in_feature(feature: dict, grid_n: int) -> list[str]:
    """
    Dado un Feature GeoJSON (círculo, polígono o rectángulo),
    devuelve lista de strings 'coord:lat,lng,zoom' para el scraper.

    grid_n: puntos por lado (1 → 1 punto, 3 → hasta 9, 5 → hasta 25, 7 → hasta 49).
    """
    if not feature:
        return []

    geom  = feature.get("geometry", {})
    props = feature.get("properties", {})
    gtype = geom.get("type", "")

    # ── Círculo ────────────────────────────────────────────────────────────────
    if gtype == "Point" and "radius" in props:
        center_lng, center_lat = geom["coordinates"]
        radius_m = float(props["radius"])
        lat_deg = radius_m / 111_320
        lng_deg = radius_m / (111_320 * math.cos(math.radians(center_lat)))

        points = []
        if grid_n == 1:
            points.append((center_lat, center_lng))
        else:
            step = 2 / (grid_n - 1)
            for i in range(grid_n):
                for j in range(grid_n):
                    lat = center_lat + (-1 + step * i) * lat_deg
                    lng = center_lng + (-1 + step * j) * lng_deg
                    if haversine_m(center_lat, center_lng, lat, lng) <= radius_m:
                        points.append((lat, lng))

        zone_r = radius_m / max(grid_n, 1)
        zoom   = _radius_to_zoom(zone_r)
        return [f"coord:{lat:.6f},{lng:.6f},{zoom}" for lat, lng in points]

    # ── Polígono / Rectángulo ─────────────────────────────────────────────────
    if gtype in ("Polygon", "MultiPolygon"):
        coords = geom["coordinates"][0] if gtype == "Polygon" else geom["coordinates"][0][0]
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)

        points = []
        if grid_n == 1:
            clat = (min_lat + max_lat) / 2
            clng = (min_lng + max_lng) / 2
            if point_in_polygon(clat, clng, coords):
                points.append((clat, clng))
        else:
            for i in range(grid_n):
                for j in range(grid_n):
                    lat = min_lat + (max_lat - min_lat) * i / (grid_n - 1)
                    lng = min_lng + (max_lng - min_lng) * j / (grid_n - 1)
                    if point_in_polygon(lat, lng, coords):
                        points.append((lat, lng))

        diag_m = haversine_m(min_lat, min_lng, max_lat, max_lng)
        zoom   = _radius_to_zoom(diag_m / max(grid_n, 1))
        return [f"coord:{lat:.6f},{lng:.6f},{zoom}" for lat, lng in points]

    return []


def feature_centroid(feature: dict) -> tuple[float, float] | None:
    """Devuelve (lat, lng) del centroide de un feature."""
    if not feature:
        return None
    geom  = feature.get("geometry", {})
    gtype = geom.get("type", "")
    if gtype == "Point":
        lng, lat = geom["coordinates"]
        return lat, lng
    if gtype in ("Polygon", "MultiPolygon"):
        coords = geom["coordinates"][0] if gtype == "Polygon" else geom["coordinates"][0][0]
        lat = sum(c[1] for c in coords) / len(coords)
        lng = sum(c[0] for c in coords) / len(coords)
        return lat, lng
    return None
