import re
from typing import List
from difflib import SequenceMatcher
from sources.base_source import Lead

class Deduplicator:
    def normalizar_nombre(self, nombre: str) -> str:
        """
        Limpia el nombre de la empresa para comparaciones:
        - Todo a minúsculas.
        - Quitar S.A.S, LTDA, S.A, puntuación.
        - Quitar espacios extras.
        """
        if not nombre: return ""
        n = nombre.lower()
        # Eliminar sufijos legales comunes en Colombia
        n = re.sub(r'\b(s\.?a\.?s\.?|ltd[aa]\.?|s\.?a\.?|e\.?u\.?|i\.?p\.?s\.?)\b', '', n)
        # Eliminar caracteres no alfanuméricos (mantener espacios)
        n = re.sub(r'[^\w\s]', '', n)
        # Quitar espacios múltiples
        n = re.sub(r'\s+', ' ', n).strip()
        return n

    def fuzzy_match(self, a: str, b: str) -> float:
        """Retorna el ratio de similitud entre dos strings."""
        return SequenceMatcher(None, a, b).ratio()

    def merge_leads(self, lead_a: Lead, lead_b: Lead) -> Lead:
        """
        Mezcla dos leads duplicados, conservando la información más completa.
        """
        # Elegir el que tenga información si el otro no
        tel = lead_a.telefono or lead_b.telefono
        email = lead_a.email or lead_b.email
        web = lead_a.sitio_web or lead_b.sitio_web
        nit = lead_a.nit or lead_b.nit
        maps_url = lead_a.maps_url or lead_b.maps_url
        
        # Unificar fuentes sin duplicados
        fuentes = list(set(lead_a.fuentes_encontrado + lead_b.fuentes_encontrado))
        
        # Conservar el rating más alto
        rating = max(filter(None, [lead_a.rating, lead_b.rating]), default=None)
        
        # Mezclar raw_data
        raw = {**lead_a.raw_data, **lead_b.raw_data}
        
        # El lead resultante hereda la mayor parte de lead_a pero con mejoras
        lead_a.telefono = tel
        lead_a.email = email
        lead_a.sitio_web = web
        lead_a.nit = nit
        lead_a.rating = rating
        lead_a.raw_data = raw
        lead_a.fuentes_encontrado = fuentes
        lead_a.tiene_web = bool(web)
        lead_a.maps_url = maps_url
        
        return lead_a

    def deduplicar(self, leads: List[Lead]) -> List[Lead]:
        """
        Lógica de deduplicación multi-fuente.
        """
        unicos: List[Lead] = []
        
        for nuevo in leads:
            duplicado_encontrado = False
            norm_nuevo = self.normalizar_nombre(nuevo.nombre)
            
            for i, existente in enumerate(unicos):
                # 1. Por NIT (100% match)
                if nuevo.nit and existente.nit and nuevo.nit == existente.nit:
                    unicos[i] = self.merge_leads(existente, nuevo)
                    duplicado_encontrado = True
                    break
                
                # 2. Por Teléfono
                if nuevo.telefono and existente.telefono and nuevo.telefono == existente.telefono:
                    unicos[i] = self.merge_leads(existente, nuevo)
                    duplicado_encontrado = True
                    break
                
                # 3. Por Nombre + Ciudad (Fuzzy Match > 85%)
                if nuevo.ciudad.lower() == existente.ciudad.lower():
                    norm_ext = self.normalizar_nombre(existente.nombre)
                    if self.fuzzy_match(norm_nuevo, norm_ext) > 0.85:
                        unicos[i] = self.merge_leads(existente, nuevo)
                        duplicado_encontrado = True
                        break
            
            if not duplicado_encontrado:
                unicos.append(nuevo)
                
        return unicos
