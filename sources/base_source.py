from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import time

from loguru import logger

@dataclass
class Lead:
    nombre: str
    ciudad: str
    nicho: str
    fuente: str          # "google_maps", "rues", "linkedin", etc.
    pais: Optional[str] = None
    departamento: Optional[str] = None
    zona: Optional[str] = None
    fuentes_encontrado: List[str] = field(default_factory=list)
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sitio_web: Optional[str] = None
    perfil_url: Optional[str] = None
    telefono_e164: Optional[str] = None
    rating: Optional[float] = None
    nit: Optional[str] = None   # para deduplicación
    lat: Optional[float] = None
    lng: Optional[float] = None
    tiene_web: bool = False
    tipo: str = "B2B"            # "B2B" o "B2C"
    sector: str = "General"
    calificacion: str = "frio"    # "oro", "bueno", "frio"
    estado: str = "Nuevo"
    maps_url: Optional[str] = None
    reseñas: int = 0
    notas: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    linkedin_empresa: Optional[str] = None
    pixel_fb: bool = False
    pixel_google: bool = False
    decisor: Optional[str] = None
    verificado: bool = False
    campaign_key: Optional[str] = None
    campaign_label: Optional[str] = None
    target_segment_key: Optional[str] = None
    target_segment: Optional[str] = None
    fit_score: int = 0
    fit_reason: Optional[str] = None
    pitch_sugerido: Optional[str] = None
    decision_roles: Optional[str] = None
    source_query: Optional[str] = None
    raw_data: dict = field(default_factory=dict) # datos originales sin procesar

    def __post_init__(self):
        if self.fuente and self.fuente not in self.fuentes_encontrado:
            self.fuentes_encontrado.append(self.fuente)

class BaseSource(ABC):
    @abstractmethod
    async def buscar(self, query: str, ciudad: str, **kwargs) -> List[Lead]:
        """
        Método principal para buscar leads en la fuente.
        """
        pass
    
    def calificar(self, lead: Lead) -> str:
        """
        Lógica de calificación por defecto.
        - Oro: No tiene web pero buen rating, o es B2B sólido.
        - Bueno: No tiene web y rating bajo/B2C, o tiene web con rating bajo.
        - Frio: Ya tiene presencia digital fuerte (web + rating bueno).
        """
        if not lead.sitio_web or not lead.tiene_web:
            if lead.rating and lead.rating >= 4.0:
                return "oro"
            if lead.tipo == "B2B":
                return "oro"
            return "bueno"
        
        if lead.rating and lead.rating < 3.5:
            return "bueno"
            
        return "frio"


def fetcher_get_with_retry(fetcher, url, retries: int = 3):
    """Obtiene una URL con Scrapling reintentando ante fallos transitorios.

    Retorna la respuesta de Scrapling o None si todos los intentos fallan.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return fetcher.get(url)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * attempt)
    logger.warning(f"Fetcher falló tras {retries} intentos para {str(url)[:80]}: {last_error}")
    return None
