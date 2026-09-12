NICHOS = {
    # ── AGROINDUSTRIA ─────────────────────────────────────────────────────────
    "lecheras": {
        "queries_maps": ["ganadería lechera", "finca lechera", "acopio de leche",
                         "planta pasteurizadora", "cooperativa lechera"],
        "queries_rues_ciiu": ["0141", "0142"],
        "densidad_grid_km": 3.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    "fincas_cafeteras": {
        "queries_maps": ["finca cafetera", "productor de café", "beneficiadero café",
                         "café especial origen", "hacienda cafetera", "tostadora de café"],
        "queries_rues_ciiu": ["0127", "1082"],
        "densidad_grid_km": 3.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    "flores_exportacion": {
        "queries_maps": ["cultivo de flores", "exportadora de flores",
                         "comercializadora internacional flores", "rosas exportación",
                         "invernadero de flores"],
        "queries_rues_ciiu": ["0119", "4620"],
        "densidad_grid_km": 3.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    "cultivos_agricolas": {
        "queries_maps": ["cultivo de frutas", "plantación agrícola", "productor agrícola",
                         "finca de aguacate", "cultivo de palma", "productor de hortalizas"],
        "queries_rues_ciiu": ["0111", "0113"],
        "densidad_grid_km": 3.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    "agroinsumos": {
        "queries_maps": ["venta de insumos agrícolas", "agroquímicos", "fertilizantes",
                         "semillas y abonos", "agroservicios", "tienda agropecuaria"],
        "queries_rues_ciiu": ["4661", "4620"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    "maquinaria_agricola": {
        "queries_maps": ["venta de tractores", "maquinaria agrícola", "implementos agrícolas",
                         "alquiler de maquinaria agrícola", "repuestos agrícolas"],
        "queries_rues_ciiu": ["4653", "7730"],
        "densidad_grid_km": 3.0,
        "tipo": "B2B",
        "sector": "agroindustria"
    },
    # ── ALIMENTOS & BEBIDAS ────────────────────────────────────────────────────
    "embutidos": {
        "queries_maps": ["planta embutidos", "fábrica embutidos",
                         "procesadora cárnica", "carnes frías productor"],
        "queries_rues_ciiu": ["1011", "1013"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    "snacks": {
        "queries_maps": ["fábrica snacks", "procesadora alimentos",
                         "platanitos industrial", "frituras industriales"],
        "queries_rues_ciiu": ["1030", "1089"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    "panaderias_industriales": {
        "queries_maps": ["panadería industrial", "fábrica de pan", "distribuidora de pan",
                         "panificación industrial", "panadería al por mayor"],
        "queries_rues_ciiu": ["1081"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    "bebidas_y_licores": {
        "queries_maps": ["productora de bebidas", "fábrica de jugos", "embotelladora",
                         "destilería", "cervecería artesanal", "agua envasada"],
        "queries_rues_ciiu": ["1101", "1104"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    "carnes_y_pescados": {
        "queries_maps": ["frigorífico", "planta de sacrificio", "distribuidora de carnes",
                         "comercializadora de pescado", "cárnicos al por mayor"],
        "queries_rues_ciiu": ["1011", "1020"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    "distribuidores_alimentos": {
        "queries_maps": ["distribuidora de alimentos", "comercializadora de víveres",
                         "alimentos al por mayor", "distribuidora de abarrotes",
                         "mayorista de alimentos"],
        "queries_rues_ciiu": ["4630"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "alimentos"
    },
    # ── SALUD & MEDICINA ───────────────────────────────────────────────────────
    "clinicas_odontologicas": {
        "queries_maps": ["clínica odontológica", "centro odontológico", "odontología estética",
                         "diseño de sonrisa", "implantes dentales", "ortodoncia"],
        "queries_rues_ciiu": ["8622"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "clinicas_medicas": {
        "queries_maps": ["clínica médica", "centro médico", "consultorio médico",
                         "centro de especialistas", "clínica general"],
        "queries_rues_ciiu": ["8610", "8621"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "hospitales": {
        "queries_maps": ["hospital privado", "clínica de alta complejidad",
                         "hospital universitario", "centro hospitalario", "ESE hospital"],
        "queries_rues_ciiu": ["8610"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "salud"
    },
    "ips_salud": {
        "queries_maps": [
            "IPS administrativo", "centro médico oficina", "clínica dirección general",
            "gerencia de salud", "IPS atención al cliente corporativo",
            "sede administrativa IPS", "laboratorio clínico gerencia"
        ],
        "queries_rues_ciiu": ["8610", "8691"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "salud"
    },
    "laboratorios_clinicos": {
        "queries_maps": ["laboratorio clínico", "laboratorio de análisis médicos",
                         "laboratorio de patología", "toma de muestras laboratorio",
                         "laboratorio imagenología"],
        "queries_rues_ciiu": ["8691"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "salud"
    },
    "farmacias": {
        "queries_maps": ["farmacia", "droguería", "farmacia 24 horas", "farmacia homeopática",
                         "droguería veterinaria"],
        "queries_rues_ciiu": ["4773"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "cirugia_estetica": {
        "queries_maps": ["clínica de cirugía estética", "clínica de cirugía plástica",
                         "cirujano plástico", "centro de cirugía estética",
                         "medicina estética y cirugía plástica"],
        "queries_rues_ciiu": ["8621"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "medicina_estetica": {
        "queries_maps": ["medicina estética", "centro de estética facial",
                         "tratamientos estéticos", "cosmiatría", "estética corporal"],
        "queries_rues_ciiu": ["8621", "9602"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "psicologos": {
        "queries_maps": ["psicólogo", "consultorio de psicología", "centro psicológico",
                         "terapia psicológica", "psicología clínica"],
        "queries_rues_ciiu": ["8690"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "fisioterapia": {
        "queries_maps": ["fisioterapia", "centro de rehabilitación física",
                         "terapia física", "rehabilitación deportiva", "fisioterapia a domicilio"],
        "queries_rues_ciiu": ["8690"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "salud"
    },
    "opticas": {
        "queries_maps": ["óptica", "optometría", "laboratorio óptico", "gafas y lentes",
                         "óptica especializada"],
        "queries_rues_ciiu": ["4772"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "salud"
    },
    "salud_ocupacional": {
        "queries_maps": ["salud ocupacional", "medicina laboral", "riesgos laborales",
                         "exámenes ocupacionales", "empresa de salud ocupacional"],
        "queries_rues_ciiu": ["8691", "8621"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "salud"
    },
    "veterinarias": {
        "queries_maps": ["clínica veterinaria", "hospital veterinario", "centro veterinario",
                         "veterinario 24 horas", "pet shop clínica"],
        "queries_rues_ciiu": ["7500"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "salud_animal"
    },
    "laboratorios_veterinarios": {
        "queries_maps": ["laboratorio veterinario", "diagnóstico veterinario",
                         "patología veterinaria", "imagenología veterinaria"],
        "queries_rues_ciiu": ["7500"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "salud_animal"
    },
    # ── GASTRONOMÍA & OCIO ─────────────────────────────────────────────────────
    "restaurantes_gourmet": {
        "queries_maps": ["restaurante gourmet", "restaurante autor", "cocina internacional",
                         "fine dining", "restaurante alta cocina"],
        "queries_rues_ciiu": ["5611"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "restaurantes": {
        "queries_maps": ["restaurante", "restaurante familiar", "restaurante con servicio a la mesa",
                         "restaurante de mariscos", "restaurante de carnes"],
        "queries_rues_ciiu": ["5611"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "cafeterias": {
        "queries_maps": ["cafetería", "café de especialidad", "coffee shop",
                         "cafetería y repostería", "café brunch"],
        "queries_rues_ciiu": ["5630"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "panaderias_pastelerias": {
        "queries_maps": ["panadería", "pastelería", "repostería", "panadería artesanal",
                         "tortas y postres", "panadería vegana"],
        "queries_rues_ciiu": ["5620"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "bares_y_pubs": {
        "queries_maps": ["bar", "pub", "taberna", "cantina", "gastrobar", "cervecería"],
        "queries_rues_ciiu": ["5630"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "comida_rapida": {
        "queries_maps": ["comida rápida", "hamburguesería", "pizzería", "asadero de pollo",
                         "comidas rápidas y domicilios", "sushi"],
        "queries_rues_ciiu": ["5619"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "heladerias": {
        "queries_maps": ["heladería", "helados artesanales", "paletería", "yogurt helado"],
        "queries_rues_ciiu": ["5613"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    "catering": {
        "queries_maps": ["servicio de catering", "catering para eventos", "buffet empresarial",
                         "alimentación empresarial", "catering corporativo"],
        "queries_rues_ciiu": ["5629"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "gastronomia"
    },
    "comida_saludable": {
        "queries_maps": ["comida saludable", "restaurante vegano", "restaurante vegetariano",
                         "comida orgánica", "delivery saludable", "batidos y bowls"],
        "queries_rues_ciiu": ["5611"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "gastronomia"
    },
    # ── SECTOR AUTOMOTRIZ ──────────────────────────────────────────────────────
    "talleres_pesados": {
        "queries_maps": ["taller mecánica tractomulas", "mantenimiento camiones",
                         "taller maquinaria pesada", "mecánica diesel", "servicio técnico camiones"],
        "queries_rues_ciiu": ["4520"],
        "densidad_grid_km": 2.5,
        "tipo": "B2B",
        "sector": "automotriz"
    },
    "talleres_mecanicos": {
        "queries_maps": ["taller mecánico", "mecánica automotriz", "taller de carros",
                         "mantenimiento de vehículos", "taller multimarca"],
        "queries_rues_ciiu": ["4520"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "automotriz"
    },
    "concesionarios": {
        "queries_maps": ["concesionario de carros", "venta de carros", "agencia de autos",
                         "concesionario multimarca", "venta de camionetas"],
        "queries_rues_ciiu": ["4511"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "automotriz"
    },
    "repuestos_autopartes": {
        "queries_maps": ["venta de repuestos", "autopartes", "repuestos para carros",
                         "repuestos y accesorios", "distribuidora de autopartes"],
        "queries_rues_ciiu": ["4530"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "automotriz"
    },
    "lavado_detailing": {
        "queries_maps": ["lavado de autos", "autolavado", "car wash", "detailing automotriz",
                         "lavado y pulido", "estética vehicular"],
        "queries_rues_ciiu": ["4520"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "automotriz"
    },
    "llantas": {
        "queries_maps": ["venta de llantas", "llantería", "centro de servicio llantas",
                         "llantas y rines", "balanceo y alineación"],
        "queries_rues_ciiu": ["4530"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "automotriz"
    },
    "motos": {
        "queries_maps": ["venta de motos", "concesionario de motos", "taller de motos",
                         "repuestos para motos", "motos y accesorios"],
        "queries_rues_ciiu": ["4540"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "automotriz"
    },
    "gruas_y_remolques": {
        "queries_maps": ["servicio de grúa", "remolque de vehículos", "grúas 24 horas",
                         "asistencia en carretera", "transporte de vehículos"],
        "queries_rues_ciiu": ["5229"],
        "densidad_grid_km": 2.0,
        "tipo": "B2C",
        "sector": "automotriz"
    },
    # ── CONSTRUCCIÓN & HOGAR ───────────────────────────────────────────────────
    "constructoras": {
        "queries_maps": ["constructora", "ingeniería y construcción", "proyectos de vivienda",
                         "edificaciones", "empresa constructora"],
        "queries_rues_ciiu": ["4111", "4112"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "construccion"
    },
    "arquitectos": {
        "queries_maps": ["estudio de arquitectura", "arquitecto", "diseño arquitectónico",
                         "arquitectura e interiorismo", "diseño de espacios"],
        "queries_rues_ciiu": ["7110"],
        "densidad_grid_km": 0.5,
        "tipo": "B2B",
        "sector": "construccion"
    },
    "ingenieria_civil": {
        "queries_maps": ["empresa de ingeniería civil", "consultoría de ingeniería",
                         "obras civiles", "gerencia de proyectos", "interventoría de obras"],
        "queries_rues_ciiu": ["7110", "7120"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "construccion"
    },
    "ferreterias_mayoristas": {
        "queries_maps": ["ferretería mayorista", "distribuidora ferretera",
                         "depósito de materiales construcción", "ferretería industrial",
                         "insumos para construcción"],
        "queries_rues_ciiu": ["4663"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "comercio"
    },
    "mueblerias": {
        "queries_maps": ["fábrica de muebles", "mueblería", "muebles a medida",
                         "venta de muebles", "muebles de cocina", "colchonería"],
        "queries_rues_ciiu": ["3100", "4759"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "cerrajeria": {
        "queries_maps": ["cerrajería", "cerrajero 24 horas", "apertura de puertas",
                         "cambio de cerraduras", "cerrajería automotriz"],
        "queries_rues_ciiu": ["8020"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "pintura_y_acabados": {
        "queries_maps": ["pintor de casas", "servicio de pintura", "pintura de edificios",
                         "acabados y remodelaciones", "drywall", "estucos y fachadas"],
        "queries_rues_ciiu": ["4330"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "electricistas": {
        "queries_maps": ["electricista", "instalaciones eléctricas", "mantenimiento eléctrico",
                         "electricista certificado", "instalación de paneles solares"],
        "queries_rues_ciiu": ["4321"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "plomeria": {
        "queries_maps": ["plomería", "fontanería", "plomero 24 horas", "reparación de fugas",
                         "servicios hidrosanitarios", "desatranques"],
        "queries_rues_ciiu": ["4322"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "reformas_y_remodelaciones": {
        "queries_maps": ["remodelaciones", "reformas de vivienda", "remodelación de cocinas",
                         "remodelación de baños", "construcción y remodelación"],
        "queries_rues_ciiu": ["4330"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "hogar"
    },
    "inmobiliarias": {
        "queries_maps": ["inmobiliaria", "bienes raíces", "finca raíz", "agencia inmobiliaria",
                         "arrendamientos y ventas", "avalúos inmobiliarios"],
        "queries_rues_ciiu": ["6810", "6820"],
        "densidad_grid_km": 0.5,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "administracion_propiedad_horizontal": {
        "queries_maps": ["administración de propiedad horizontal", "administración de edificios",
                         "administración de conjuntos", "administrador de copropiedades",
                         "aseguradoras propiedad horizontal"],
        "queries_rues_ciiu": ["6830"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "mudanzas_y_fletes": {
        "queries_maps": ["mudanzas", "fletes", "empresa de mudanzas", "transporte de mudanzas",
                         "embalaje y mudanzas"],
        "queries_rues_ciiu": ["4942"],
        "densidad_grid_km": 1.5,
        "tipo": "B2C",
        "sector": "logistica"
    },
    # ── BELLEZA & BIENESTAR ────────────────────────────────────────────────────
    "centros_estetica": {
        "queries_maps": ["centro de estética", "spa facial", "clínica de belleza",
                         "estética integral", "tratamientos corporales"],
        "queries_rues_ciiu": ["9602"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "peluquerias": {
        "queries_maps": ["peluquería", "salón de belleza", "estilista", "salón de peinados",
                         "peluquería y estética"],
        "queries_rues_ciiu": ["9602"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "barberias": {
        "queries_maps": ["barbería", "barbero", "barber shop", "corte de cabello",
                         "barbería premium"],
        "queries_rues_ciiu": ["9602"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "spas": {
        "queries_maps": ["spa", "centro de bienestar", "masajes", "spa de relajación",
                         "spa y terapias", "baños de vapor"],
        "queries_rues_ciiu": ["9602"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "uñas": {
        "queries_maps": ["centro de uñas", "manicure y pedicure", "uñas acrílicas",
                         "nail art", "estudio de uñas"],
        "queries_rues_ciiu": ["9602"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "gimnasios": {
        "queries_maps": ["gimnasio", "centro de fitness", "crossfit center", "gym",
                         "entrenamiento funcional", "gimnasio 24 horas"],
        "queries_rues_ciiu": ["9311"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "yoga_pilates": {
        "queries_maps": ["estudio de yoga", "pilates", "yoga studio", "yoga y meditación",
                         "centro de pilates"],
        "queries_rues_ciiu": ["9311"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "tatuajes": {
        "queries_maps": ["estudio de tatuajes", "tatuador", "piercing", "tattoo studio",
                         "perforaciones"],
        "queries_rues_ciiu": ["9609"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "bienestar"
    },
    "canchas_sinteticas": {
        "queries_maps": ["cancha sintética", "cancha de fútbol sintética",
                         "alquiler de canchas de fútbol", "cancha de fútbol 5",
                         "complejo de canchas sintéticas"],
        "queries_rues_ciiu": ["9311"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "entretenimiento"
    },
# ── PROFESIONALES & LEGAL ──────────────────────────────────────────────────
    "abogados": {
        "queries_maps": ["firma de abogados", "bufete de abogados", "asesoría jurídica",
                         "consultorio jurídico", "abogados especializados"],
        "queries_rues_ciiu": ["6910"],
        "densidad_grid_km": 0.5,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "contadores": {
        "queries_maps": ["firma contable", "oficina de contadores", "revisoría fiscal",
                         "auditoría contable", "asesoría tributaria"],
        "queries_rues_ciiu": ["6920"],
        "densidad_grid_km": 0.5,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "notarias": {
        "queries_maps": ["notaría", "notaría pública", "autenticación de documentos",
                         "trámites notariales", "notaría y registro"],
        "queries_rues_ciiu": ["6910"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "servicios"
    },
    "asesores_fiscales": {
        "queries_maps": ["asesoría tributaria", "asesor fiscal", "impuestos y declaraciones",
                         "consultoría fiscal", "contadores públicos"],
        "queries_rues_ciiu": ["6920"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "consultoria_empresarial": {
        "queries_maps": ["consultoría empresarial", "consultoría de gestión", "consultoría estratégica",
                         "consultoría organizacional", "consultores de negocios"],
        "queries_rues_ciiu": ["7020"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "agencia_marketing": {
        "queries_maps": ["agencia de marketing digital", "agencia de publicidad",
                         "marketing digital", "agencia de branding", "agencia de pauta digital"],
        "queries_rues_ciiu": ["7310"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "recursos_humanos": {
        "queries_maps": ["empresa de recursos humanos", "outsourcing de personal",
                         "selección de personal", "consultoría de talento humano",
                         "headhunter"],
        "queries_rues_ciiu": ["7830"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "seguridad_privada": {
        "queries_maps": ["empresa seguridad privada", "vigilancia y seguridad", "escoltas",
                         "seguridad electrónica", "empresa de vigilancia"],
        "queries_rues_ciiu": ["8010"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "limpieza_industrial": {
        "queries_maps": ["limpieza industrial", "aseo y mantenimiento empresas",
                         "limpieza de fachadas", "desinfección industrial", "aseo profesional"],
        "queries_rues_ciiu": ["8121", "8129"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "servicios"
    },
    "agencias_seguros": {
        "queries_maps": ["agencia de seguros", "asesoría de seguros", "corredor de seguros",
                         "seguros de vida", "seguros empresariales", "pólizas de seguros"],
        "queries_rues_ciiu": ["6512", "6622"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "finanzas"
    },
    "asesorias_financieras": {
        "queries_maps": ["asesoría financiera", "consultoría financiera", "asesor de inversiones",
                         "planeación financiera", "factoring", "créditos empresariales"],
        "queries_rues_ciiu": ["6619", "6492"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "finanzas"
    },
    # ── INDUSTRIA & MANUFACTURA ────────────────────────────────────────────────
    "fabrica_calzado": {
        "queries_maps": ["fábrica de calzado", "industria del cuero", "zapatería fabricante",
                         "taller de zapatos", "manufactura calzado"],
        "queries_rues_ciiu": ["1520"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "confecciones": {
        "queries_maps": ["fábrica de ropa", "confecciones", "taller de costura industrial",
                         "textiles fabricación", "maquila de ropa"],
        "queries_rues_ciiu": ["1410"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "metalmecanica": {
        "queries_maps": ["metalmecánica", "fábrica de estructuras metálicas", "torneado y fresado",
                         "soldadura industrial", "maquinado CNC", "carpintería metálica"],
        "queries_rues_ciiu": ["2511", "2599"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "plasticos_y_empaques": {
        "queries_maps": ["fábrica de plásticos", "inyección de plástico", "empaques industriales",
                         "fábrica de bolsas plásticas", "envases plásticos", "termoformado"],
        "queries_rues_ciiu": ["2220", "2222"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "quimicos_y_pinturas": {
        "queries_maps": ["fábrica de pinturas", "productos químicos industriales",
                         "fábrica de jabones", "desinfectantes", "productos de aseo industrial"],
        "queries_rues_ciiu": ["2021", "2022"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "textiles": {
        "queries_maps": ["fábrica textil", "hilandería", "tejeduría", "telas y tejidos",
                         "estampación textil", "producción de telas"],
        "queries_rues_ciiu": ["1311", "1312"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "maquinaria_pesada": {
        "queries_maps": ["alquiler maquinaria pesada", "retroexcavadoras alquiler",
                         "maquinaria construcción", "venta maquinaria amarilla", "gruas alquiler"],
        "queries_rues_ciiu": ["7730"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "construccion"
    },
    "imprentas": {
        "queries_maps": ["imprenta", "litografía", "impresión digital", "imprenta offset",
                         "impresión de empaques", "serigrafía"],
        "queries_rues_ciiu": ["1811", "1812"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "manufactura"
    },
    "control_plagas": {
        "queries_maps": ["control de plagas", "fumigación", "control de roedores",
                         "desinsectación", "manejo integrado de plagas"],
        "queries_rues_ciiu": ["8129"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "servicios"
    },
    # ── LOGÍSTICA & TRANSPORTE ─────────────────────────────────────────────────
    "logistica": {
        "queries_maps": ["empresa de logística", "transporte de carga", "operador logístico",
                         "bodegaje", "distribución nacional"],
        "queries_rues_ciiu": ["4923", "5210", "5229"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "logistica"
    },
    "bodegas_y_almacenamiento": {
        "queries_maps": ["bodega de almacenamiento", "almacenamiento y logística",
                         "bodegas en arriendo", "centro de distribución", "bodegaje industrial"],
        "queries_rues_ciiu": ["5210"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "logistica"
    },
    "mensajeria": {
        "queries_maps": ["servicio de mensajería", "mensajería empresarial", "paquetería",
                         "mensajero urbano", "servicio de domicilios", "courier"],
        "queries_rues_ciiu": ["5320"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "logistica"
    },
    "transporte_pasajeros": {
        "queries_maps": ["empresa de transporte", "transporte especial de pasajeros",
                         "servicio de buses", "transporte escolar", "empresa de taxis"],
        "queries_rues_ciiu": ["4921"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "logistica"
    },
    # ── TECNOLOGÍA ─────────────────────────────────────────────────────────────
    "software_dev": {
        "queries_maps": ["empresa de software", "desarrollo web y móvil", "agencia digital software",
                         "consultoría tecnológica", "casa de software"],
        "queries_rues_ciiu": ["6201", "6202"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "tecnologia"
    },
    "reparacion_celulares": {
        "queries_maps": ["reparación de celulares", "servicio técnico celulares",
                         "reparación de smartphones", "cambio de pantalla", "servicio técnico móviles"],
        "queries_rues_ciiu": ["9512"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "tecnologia"
    },
    "soporte_tecnico": {
        "queries_maps": ["soporte técnico de computadores", "servicio técnico de PC",
                         "mantenimiento de computadores", "reparación de computadores",
                         "soporte informático empresarial"],
        "queries_rues_ciiu": ["9511"],
        "densidad_grid_km": 0.8,
        "tipo": "B2B",
        "sector": "tecnologia"
    },
    "cctv_y_seguridad_electronica": {
        "queries_maps": ["instalación de cámaras de seguridad", "CCTV", "circuito cerrado de televisión",
                         "control de acceso", "sistemas de alarma", "videovigilancia"],
        "queries_rues_ciiu": ["8020", "4321"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "tecnologia"
    },
    "venta_electronica": {
        "queries_maps": ["venta de electrónica", "tienda de tecnología", "computadores y accesorios",
                         "venta de tablets y celulares", "tienda de electrónica"],
        "queries_rues_ciiu": ["4659", "4741"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "tecnologia"
    },
    "telecomunicaciones": {
        "queries_maps": ["proveedor de internet", "empresa de telecomunicaciones", "internet fibra óptica",
                         "proveedor de internet empresarial", "redes y telecomunicaciones"],
        "queries_rues_ciiu": ["6110", "6190"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "tecnologia"
    },
    # ── EDUCACIÓN ──────────────────────────────────────────────────────────────
    "colegios": {
        "queries_maps": ["colegio privado", "institución educativa privada",
                         "colegio bilingüe", "liceo", "gimnasio escolar"],
        "queries_rues_ciiu": ["8510", "8520"],
        "densidad_grid_km": 0.5,
        "tipo": "B2B",
        "sector": "educacion"
    },
    "jardines_infantiles": {
        "queries_maps": ["jardín infantil", "preescolar", "guardería", "jardín de niños",
                         "centro de desarrollo infantil"],
        "queries_rues_ciiu": ["8511"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "educacion"
    },
    "universidades": {
        "queries_maps": ["universidad", "institución universitaria", "centro de educación superior",
                         "universidad tecnológica", "campus universitario"],
        "queries_rues_ciiu": ["8530"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "educacion"
    },
    "academias_idiomas": {
        "queries_maps": ["academia de idiomas", "clases de inglés", "escuela de idiomas",
                         "centro de idiomas", "inglés empresarial"],
        "queries_rues_ciiu": ["8559"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "educacion"
    },
    "escuelas_conduccion": {
        "queries_maps": ["escuela de conducción", "autoescuela", "clases de manejo",
                         "escuela de manejo", "centro de enseñanza automovilística"],
        "queries_rues_ciiu": ["8559"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "educacion"
    },
    "formacion_tecnica": {
        "queries_maps": ["centro de formación técnica", "instituto técnico", "cursos técnicos",
                         "educación tecnológica", "formación para el trabajo"],
        "queries_rues_ciiu": ["8541", "8559"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "educacion"
    },
    # ── MODA & RETAIL ──────────────────────────────────────────────────────────
    "tiendas_ropa": {
        "queries_maps": ["tienda de ropa", "boutique", "ropa de moda", "tienda de vestuario",
                         "ropa deportiva", "ropa casual"],
        "queries_rues_ciiu": ["4771"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "moda"
    },
    "zapaterias": {
        "queries_maps": ["zapatería", "venta de calzado", "zapatos", "calzado deportivo",
                         "tienda de zapatos"],
        "queries_rues_ciiu": ["4772"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "moda"
    },
    "joyerias": {
        "queries_maps": ["joyería", "bisutería", "venta de joyas", "relojería",
                         "joyería y relojería"],
        "queries_rues_ciiu": ["4774"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "moda"
    },
    "supermercados": {
        "queries_maps": ["supermercado", "mercado", "tienda de barrio", "supermercado mayorista",
                         "minimercado"],
        "queries_rues_ciiu": ["4711"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "retail"
    },
    "tiendas_deportivas": {
        "queries_maps": ["tienda deportiva", "artículos deportivos", "tienda de deportes",
                         "ropa deportiva y accesorios", "bicicletas y deportes"],
        "queries_rues_ciiu": ["4762"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "moda"
    },
    "cosmeticos": {
        "queries_maps": ["tienda de cosméticos", "perfumería", "venta de cosméticos",
                         "productos de belleza", "tienda de maquillaje"],
        "queries_rues_ciiu": ["4773"],
        "densidad_grid_km": 0.3,
        "tipo": "B2C",
        "sector": "retail"
    },
    # ── TURISMO & EVENTOS ──────────────────────────────────────────────────────
    "hoteles_boutique": {
        "queries_maps": ["hotel boutique", "hostal de lujo", "glamping de lujo",
                         "alojamiento exclusivo", "hotel con encanto"],
        "queries_rues_ciiu": ["5511"],
        "densidad_grid_km": 1.0,
        "tipo": "B2C",
        "sector": "turismo"
    },
    "hoteles": {
        "queries_maps": ["hotel", "hospedaje", "hostal", "hotel centro", "hotel económico"],
        "queries_rues_ciiu": ["5511", "5520"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "turismo"
    },
    "agencia_turismo": {
        "queries_maps": ["agencia de viajes", "operador turístico", "tours",
                         "agencia de turismo", "viajes y excursiones"],
        "queries_rues_ciiu": ["7911", "7912"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "turismo"
    },
    "salones_eventos": {
        "queries_maps": ["salón de eventos", "salón de fiestas", "salón de recepciones",
                         "centro de eventos", "salón para cumpleaños"],
        "queries_rues_ciiu": ["8230"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "eventos"
    },
    "campestres": {
        "queries_maps": ["club campestre", "finca para eventos",
                         "hacienda eventos", "salón campestre", "finca recreacional"],
        "queries_rues_ciiu": ["5520"],
        "densidad_grid_km": 1.5,
        "tipo": "B2C",
        "sector": "entretenimiento"
    },
    "fotografos": {
        "queries_maps": ["fotógrafo profesional", "estudio fotográfico", "fotografía de eventos",
                         "fotografía empresarial", "video profesional"],
        "queries_rues_ciiu": ["7420"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "eventos"
    },
    "organizacion_eventos": {
        "queries_maps": ["organización de eventos", "empresa de eventos corporativos",
                         "eventos empresariales", "producción de eventos", "coordinación de eventos"],
        "queries_rues_ciiu": ["8230"],
        "densidad_grid_km": 1.0,
        "tipo": "B2B",
        "sector": "eventos"
    },
    "turismo_aventura": {
        "queries_maps": ["turismo de aventura", "ecoturismo", "parapente", "rafting",
                         "caminatas ecológicas", "turismo rural"],
        "queries_rues_ciiu": ["7911", "9329"],
        "densidad_grid_km": 2.0,
        "tipo": "B2C",
        "sector": "turismo"
    },
    # ── MEDIO AMBIENTE & ENERGÍA ───────────────────────────────────────────────
    "aguas_residuales": {
        "queries_maps": ["PTAR", "tratamiento aguas industriales",
                         "planta tratamiento aguas residuales", "ingeniería ambiental"],
        "queries_rues_ciiu": ["3700", "3900"],
        "densidad_grid_km": 5.0,
        "tipo": "B2B",
        "sector": "medio_ambiente"
    },
    "reciclaje": {
        "queries_maps": ["empresa de reciclaje", "reciclaje de residuos", "centro de acopio",
                         "gestión de residuos", "reciclaje industrial", "chatarrería"],
        "queries_rues_ciiu": ["3830"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "medio_ambiente"
    },
    "energias_renovables": {
        "queries_maps": ["instalación de paneles solares", "energía solar", "energías renovables",
                         "instalación solar fotovoltaica", "mantenimiento de paneles solares"],
        "queries_rues_ciiu": ["4321", "3511"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "energia"
    },
    "ingenieria_ambiental": {
        "queries_maps": ["consultoría ambiental", "ingeniería ambiental", "estudios de impacto ambiental",
                         "gestión ambiental empresarial", "licenciamiento ambiental"],
        "queries_rues_ciiu": ["7110", "3900"],
        "densidad_grid_km": 2.0,
        "tipo": "B2B",
        "sector": "medio_ambiente"
    },
    # ── MASCOTAS ───────────────────────────────────────────────────────────────
    "peluqueria_canina": {
        "queries_maps": ["peluquería canina", "dog grooming", "peluquería para perros",
                         "estética canina", "baño y corte para mascotas"],
        "queries_rues_ciiu": ["9609"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "mascotas"
    },
    "tiendas_mascotas": {
        "queries_maps": ["tienda de mascotas", "pet shop", "veterinaria y pet shop",
                         "accesorios para mascotas", "alimentos para mascotas"],
        "queries_rues_ciiu": ["4789"],
        "densidad_grid_km": 0.5,
        "tipo": "B2C",
        "sector": "mascotas"
    },
    # ── COMUNICACIÓN & MEDIOS ──────────────────────────────────────────────────
    "medios_comunicacion": {
        "queries_maps": ["emisora de radio", "canal de televisión", "periódico digital",
                         "medio de comunicación", "productora audiovisual"],
        "queries_rues_ciiu": ["6010", "6020", "5911"],
        "densidad_grid_km": 1.5,
        "tipo": "B2B",
        "sector": "comunicacion"
    },
    # ── DEPORTES & RECREACIÓN ──────────────────────────────────────────────────
    "centros_deportivos": {
        "queries_maps": ["centro deportivo", "club deportivo", "cancha de fútbol",
                         "polideportivo", "complejo deportivo", "piscina pública"],
        "queries_rues_ciiu": ["9311"],
        "densidad_grid_km": 1.0,
        "tipo": "B2C",
        "sector": "deportes"
    },
    "academias_deportivas": {
        "queries_maps": ["escuela de fútbol", "academia de natación", "escuela de tenis",
                         "academia de artes marciales", "escuela de baloncesto"],
        "queries_rues_ciiu": ["9312", "8559"],
        "densidad_grid_km": 0.8,
        "tipo": "B2C",
        "sector": "deportes"
    },
}
