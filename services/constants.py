import unicodedata


NICHOS_DICT = {
    "TODO EL MERCADO": ["TODOS LOS NEGOCIOS (Barrido Total)", "Empresas locales", "Servicios profesionales"],
    "SALUD & MEDICINA": ["TODOS LOS SUBNICHOS (Sector Salud)", "IPS de Salud (con Gerencia)", "Odontólogos", "Clínicas Médicas", "Clínicas de Cirugía Estética", "Psicólogos", "Fisioterapeutas", "Ópticas", "Dermatólogos", "Ginecólogos", "Pediatras", "Veterinarias"],
    "GASTRONOMÍA & OCIO": ["TODOS LOS SUBNICHOS (Sector Gastro)", "Restaurantes", "Cafeterías", "Pizzerías", "Hamburgueserías", "Panaderías", "Bares", "Sushi", "Comida Vegana"],
    "SECTOR AUTOMOTRIZ": ["TODOS LOS SUBNICHOS (Sector Motor)", "Talleres Mecánicos", "Concesionarios", "Venta de Repuestos", "Lavado de Autos", "Centros de Diagnóstico", "Motos"],
    "CONSTRUCCIÓN & HOGAR": ["TODOS LOS SUBNICHOS (Sector Hogar)", "Inmobiliarias", "Arquitectos", "Constructoras", "Ferreterías", "Reformas", "Cerrajeros", "Mueblerías"],
    "BELLEZA & BIENESTAR": ["TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Barberías", "Spas", "Centros de Uñas", "Gimnasios", "Canchas Sintéticas", "Yoga", "Tatuajes"],
    "PROFESIONALES & LEGAL": ["TODOS LOS SUBNICHOS (Sector Profesional)", "Abogados", "Contadores", "Notarías", "Asesores Fiscales", "Agencias de Seguros", "Agencias de Marketing"],
    "INDUSTRIAL & TÉCNICO": ["TODOS LOS SUBNICHOS (Sector Industrial)", "Fábricas", "Logística", "Mantenimiento", "Control de Plagas", "Textiles", "Metalúrgicas"],
    "EDUCACIÓN": ["TODOS LOS SUBNICHOS (Sector Educación)", "Colegios", "Jardines Infantiles", "Academias de Idiomas", "Universidades", "Escuelas de Conducción"],
    "TECNOLOGÍA": ["TODOS LOS SUBNICHOS (Sector Tech)", "Reparación de Celulares", "Soporte Técnico", "Desarrollo Web", "Venta de Electrónica", "CCTV"],
    "MODA & RETAIL": ["TODOS LOS SUBNICHOS (Sector Moda)", "Tiendas de Ropa", "Zapaterías", "Joyerías", "Supermercados", "Tiendas Deportivas"],
    "MASCOTAS": ["TODOS LOS SUBNICHOS (Sector Mascotas)", "Veterinarias", "Peluquería Canina", "Tiendas de Mascotas"],
    "EVENTOS & TURISMO": ["TODOS LOS SUBNICHOS (Sector Turismo)", "Hoteles", "Salones de Eventos", "Fotógrafos", "Agencias de Viajes"],
    "SERVICIOS EMPRESARIALES": ["TODOS LOS SUBNICHOS (Sector B2B)", "Seguridad Privada", "Mensajería", "Mudanzas", "Imprentas"],
    "GESTIÓN DE AGUAS & AMBIENTAL": ["TODOS LOS SUBNICHOS (Sector Agua)", "Plantas de Tratamiento de Aguas", "Transporte de Aguas Residuales", "Succión de Pozos Sépticos", "Servicios de Vactor", "Ingeniería Ambiental"],
}

STATUS_COLORS = {
    "Nuevo":       {"color": "#FF0000", "fill": "#FF0000", "opacity": 0.9},
    "Contactado":  {"color": "#6EB4C9", "fill": "#6EB4C9", "opacity": 0.85},
    "Interesado":  {"color": "#A06EC9", "fill": "#A06EC9", "opacity": 0.9},
    "Cerrado":     {"color": "#4ADE80", "fill": "#4ADE80", "opacity": 0.95},
    "Descartado":  {"color": "#555568", "fill": "#444455", "opacity": 0.5},
    "Sin WhatsApp": {"color": "#555568", "fill": "#444455", "opacity": 0.5},
}

COUNTRY_CODES = {
    "Colombia": "57", "España": "34", "México": "52", "Argentina": "54",
    "Chile": "56", "Perú": "51", "Ecuador": "593", "Venezuela": "58",
    "Estados Unidos": "1", "Panamá": "507",
}

NICHO_SYNONYMS = {
    "IPS de Salud (con Gerencia)": ["Gerencia IPS", "Administración Salud", "Dirección Médica"],
    "Odontólogos":            ["Dentistas", "Clínica dental"],
    "Clínicas Médicas":       ["Centro médico", "Consultorio médico"],
    "Clínicas de Cirugía Estética": ["Cirugía plástica", "Clínica de cirugía plástica", "Centro de cirugía estética"],
    "Psicólogos":             ["Psicología", "Terapeuta"],
    "Fisioterapeutas":        ["Fisioterapia", "Rehabilitación física"],
    "Ópticas":                ["Optometría", "Óptico"],
    "Dermatólogos":           ["Dermatología", "Clínica estética"],
    "Ginecólogos":            ["Ginecología"],
    "Pediatras":              ["Pediatría", "Médico pediatra"],
    "Veterinarias":           ["Veterinario", "Clínica veterinaria"],
    "Restaurantes":           ["Restaurant", "Comida", "Almuerzo"],
    "Cafeterías":             ["Café", "Coffee shop"],
    "Pizzerías":              ["Pizza", "Pizzería"],
    "Hamburgueserías":        ["Hamburguesas", "Burger"],
    "Panaderías":             ["Pastelería", "Repostería"],
    "Bares":                  ["Bar", "Taberna", "Cantina"],
    "Sushi":                  ["Japonés", "Sushi bar"],
    "Comida Vegana":          ["Restaurante vegano", "Comida saludable"],
    "Talleres Mecánicos":     ["Mecánica automotriz", "Taller de carros"],
    "Concesionarios":         ["Venta de carros", "Agencia de autos"],
    "Venta de Repuestos":     ["Repuestos", "Autopartes"],
    "Lavado de Autos":        ["Car wash", "Autolavado", "Lavadero"],
    "Motos":                  ["Motocicletas", "Venta de motos"],
    "Inmobiliarias":          ["Bienes raíces", "Finca raíz", "Arriendos"],
    "Constructoras":          ["Construcción", "Contratista"],
    "Ferreterías":            ["Materiales de construcción"],
    "Reformas":               ["Remodelaciones", "Acabados"],
    "Cerrajeros":             ["Cerrajería"],
    "Mueblerías":             ["Muebles"],
    "Peluquerías":            ["Salón de belleza", "Estilista"],
    "Barberías":              ["Barbería", "Barbero"],
    "Spas":                   ["Centro de bienestar", "Masajes"],
    "Centros de Uñas":        ["Manicure", "Uñas acrílicas"],
    "Gimnasios":              ["Gym", "Fitness", "Centro deportivo"],
    "Canchas Sintéticas":     ["Cancha de fútbol sintética", "Alquiler de canchas", "Fútbol 5"],
    "Yoga":                   ["Yoga studio", "Pilates"],
    "Tatuajes":               ["Estudio de tatuajes", "Piercing"],
    "Abogados":               ["Bufete", "Estudio jurídico"],
    "Contadores":             ["Contador público", "Asesor contable"],
    "Notarías":               ["Notario"],
    "Agencias de Seguros":    ["Seguros", "Aseguradora"],
    "Agencias de Marketing":  ["Marketing digital", "Publicidad"],
    "Logística":              ["Transporte", "Courier"],
    "Mantenimiento":          ["Plomería", "Electricista", "Servicios del hogar"],
    "Control de Plagas":      ["Fumigación"],
    "Colegios":               ["Institución educativa", "Escuela"],
    "Jardines Infantiles":    ["Preescolar", "Guardería"],
    "Academias de Idiomas":   ["Clases de inglés", "Escuela de idiomas"],
    "Escuelas de Conducción": ["Autoescuela", "Clases de manejo"],
    "Reparación de Celulares":["Servicio técnico celulares"],
    "Soporte Técnico":        ["Técnico de sistemas", "Servicio técnico PC"],
    "Desarrollo Web":         ["Páginas web", "Diseño web"],
    "CCTV":                   ["Cámaras de seguridad"],
    "Tiendas de Ropa":        ["Boutique", "Ropa"],
    "Zapaterías":             ["Calzado"],
    "Joyerías":               ["Bisutería"],
    "Tiendas Deportivas":     ["Artículos deportivos"],
    "Peluquería Canina":      ["Dog grooming", "Peluquería para perros"],
    "Tiendas de Mascotas":    ["Pet shop"],
    "Hoteles":                ["Hospedaje", "Hostal"],
    "Salones de Eventos":     ["Salón de fiestas"],
    "Fotógrafos":             ["Estudio fotográfico"],
    "Agencias de Viajes":     ["Tour operador", "Viajes"],
    "Seguridad Privada":      ["Vigilancia"],
    "Mensajería":             ["Delivery", "Paquetería"],
    "Mudanzas":               ["Fletes"],
    "Imprentas":              ["Litografía", "Papelería"],
    "Empresas locales":       ["Negocios locales"],
    "Servicios profesionales":["Profesionales independientes"],
}

OFFER_SUGGESTIONS = {
    "barberias": "Chatbot de WhatsApp para reservas, agenda automática y recordatorios de citas.",
    "clinicas de cirugia estetica": "Sistema de citas, chatbot para valoración inicial y CRM de seguimiento de pacientes.",
    "restaurantes": "Página web con menú, reservas o pedidos y chatbot de atención por WhatsApp.",
    "cafeterias": "Página web con menú, pedidos anticipados y programa digital de fidelización.",
    "inmobiliarias": "Página web de inmuebles, CRM comercial y chatbot para calificar interesados.",
    "joyerias": "Catálogo o tienda virtual y chatbot para consultas, cotizaciones y seguimiento.",
    "talleres mecanicos": "Sistema de citas, cotizaciones y recordatorios automáticos de mantenimiento.",
    "constructoras": "Página web de proyectos y CRM a medida para captar y dar seguimiento a compradores.",
    "lavado de autos": "Página web con reservas, planes recurrentes y recordatorios por WhatsApp.",
    "gimnasios": "Sistema de membresías, reservas de clases y chatbot para captar nuevos inscritos.",
    "canchas sinteticas": "Página web y chatbot para consultar horarios, reservar y confirmar pagos.",
    "colegios": "Portal web de admisiones y chatbot para matrículas, preguntas y agendamiento de visitas.",
}


def _normalize_niche(value):
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def get_offer_suggestion(niche, has_website=None):
    """Devuelve una oferta concreta según el nicho y la presencia web del negocio."""
    normalized = _normalize_niche(niche)
    suggestion = OFFER_SUGGESTIONS.get(normalized)
    if suggestion is None:
        for niche_key, niche_suggestion in OFFER_SUGGESTIONS.items():
            if niche_key in normalized or normalized in niche_key:
                suggestion = niche_suggestion
                break

    if suggestion is None:
        suggestion = "Software a medida para automatizar reservas, atención al cliente o seguimiento comercial."

    if has_website is not None and not bool(has_website) and "pagina web" not in _normalize_niche(suggestion):
        return f"Página web profesional + {suggestion[0].lower()}{suggestion[1:]}"
    return suggestion
