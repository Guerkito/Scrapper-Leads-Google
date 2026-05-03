from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Lead:
    nombre: str
    ciudad: str
    nicho: str
    fuente: str          # "google_maps", "rues", "linkedin", etc.
    fuentes_encontrado: List[str] = field(default_factory=list)
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    sitio_web: Optional[str] = None
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
        - Oro: No tiene web pero tiene buen rating o es B2B sólido.
        - Bueno: Tiene web pero rating medio, o sin web y rating bajo.
        - Frio: Datos incompletos o ya tiene presencia digital fuerte.
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
