import unicodedata


NICHOS_DICT = {
    "TODO EL MERCADO": ["TODOS LOS NEGOCIOS (Barrido Total)", "Empresas locales", "Servicios profesionales"],
    "SALUD & MEDICINA": [
        "TODOS LOS SUBNICHOS (Sector Salud)", "IPS de Salud (con Gerencia)", "Hospitales y Clínicas",
        "Odontólogos", "Laboratorios Clínicos", "Farmacias y Droguerías", "Medicina Estética",
        "Clínicas de Cirugía Estética", "Psicólogos", "Fisioterapeutas", "Ópticas",
        "Salud Ocupacional", "Dermatólogos", "Ginecólogos", "Pediatras", "Veterinarias",
    ],
    "GASTRONOMÍA & OCIO": [
        "TODOS LOS SUBNICHOS (Sector Gastro)", "Restaurantes", "Cafeterías", "Pizzerías",
        "Hamburgueserías", "Panaderías y Reposterías", "Bares y Pubs", "Sushi", "Comida Vegana",
        "Heladerías", "Catering", "Comida Rápida",
    ],
    "SECTOR AUTOMOTRIZ": [
        "TODOS LOS SUBNICHOS (Sector Motor)", "Talleres Mecánicos", "Concesionarios",
        "Venta de Repuestos", "Lavado y Detailing", "Venta de Llantas", "Centros de Diagnóstico",
        "Motos", "Grúas y Remolques",
    ],
    "CONSTRUCCIÓN & HOGAR": [
        "TODOS LOS SUBNICHOS (Sector Hogar)", "Inmobiliarias", "Arquitectos", "Ingeniería Civil",
        "Constructoras", "Ferreterías", "Reformas y Remodelaciones", "Cerrajeros", "Mueblerías",
        "Pintores y Acabados", "Electricistas", "Plomería", "Administración de Propiedad Horizontal",
    ],
    "BELLEZA & BIENESTAR": [
        "TODOS LOS SUBNICHOS (Sector Belleza)", "Peluquerías", "Barberías", "Spas y Masajes",
        "Centros de Uñas", "Gimnasios", "Canchas Sintéticas", "Yoga y Pilates", "Tatuajes",
        "Centros de Estética",
    ],
    "PROFESIONALES & LEGAL": [
        "TODOS LOS SUBNICHOS (Sector Profesional)", "Abogados", "Contadores", "Notarías",
        "Asesores Fiscales", "Agencias de Seguros", "Agencias de Marketing",
        "Consultoría Empresarial", "Recursos Humanos",
    ],
    "INDUSTRIAL & TÉCNICO": [
        "TODOS LOS SUBNICHOS (Sector Industrial)", "Fábricas y Manufactura", "Metalmecánica",
        "Plásticos y Empaques", "Químicos y Pinturas", "Textiles", "Imprentas",
        "Logística y Bodegas", "Mantenimiento", "Control de Plagas", "Maquinaria Pesada",
    ],
    "EDUCACIÓN": [
        "TODOS LOS SUBNICHOS (Sector Educación)", "Colegios", "Jardines Infantiles",
        "Academias de Idiomas", "Universidades", "Formación Técnica", "Escuelas de Conducción",
    ],
    "TECNOLOGÍA": [
        "TODOS LOS SUBNICHOS (Sector Tech)", "Reparación de Celulares", "Soporte Técnico",
        "Desarrollo Web", "Venta de Electrónica", "CCTV y Seguridad Electrónica",
        "Telecomunicaciones e Internet",
    ],
    "MODA & RETAIL": [
        "TODOS LOS SUBNICHOS (Sector Moda)", "Tiendas de Ropa", "Zapaterías", "Joyerías",
        "Supermercados", "Tiendas Deportivas", "Cosméticos y Perfumerías",
    ],
    "MASCOTAS": [
        "TODOS LOS SUBNICHOS (Sector Mascotas)", "Veterinarias", "Peluquería Canina",
        "Tiendas de Mascotas",
    ],
    "EVENTOS & TURISMO": [
        "TODOS LOS SUBNICHOS (Sector Turismo)", "Hoteles", "Hoteles Boutique", "Salones de Eventos",
        "Fotógrafos", "Agencias de Viajes", "Organización de Eventos", "Turismo de Aventura",
    ],
    "SERVICIOS EMPRESARIALES": [
        "TODOS LOS SUBNICHOS (Sector B2B)", "Seguridad Privada", "Mensajería y Paquetería",
        "Mudanzas y Fletes", "Imprentas", "Limpieza Industrial", "Consultoría Empresarial",
    ],
    "GESTIÓN DE AGUAS & AMBIENTAL": [
        "TODOS LOS SUBNICHOS (Sector Agua)", "Plantas de Tratamiento de Aguas",
        "Transporte de Aguas Residuales", "Succión de Pozos Sépticos", "Servicios de Vactor",
        "Ingeniería Ambiental", "Reciclaje y Residuos", "Energías Renovables",
    ],
    "AGROINDUSTRIA": [
        "TODOS LOS SUBNICHOS (Sector Agro)", "Ganadería y Lecherías", "Fincas Cafeteras",
        "Flores y Exportación", "Cultivos Agrícolas", "Insumos Agrícolas", "Maquinaria Agrícola",
    ],
    "ALIMENTOS & BEBIDAS": [
        "TODOS LOS SUBNICHOS (Sector Alimentos)", "Embutidos y Cárnicos", "Fábricas de Snacks",
        "Panaderías Industriales", "Bebidas y Licores", "Distribuidoras de Alimentos",
    ],
    "FINANZAS & SEGUROS": [
        "TODOS LOS SUBNICHOS (Sector Finanzas)", "Agencias de Seguros", "Asesorías Financieras",
    ],
    "DEPORTES & RECREACIÓN": [
        "TODOS LOS SUBNICHOS (Sector Deportes)", "Centros Deportivos", "Academias Deportivas",
    ],
    "COMUNICACIÓN & MEDIOS": [
        "TODOS LOS SUBNICHOS (Sector Medios)", "Medios de Comunicación",
    ],
}

STATUS_COLORS = {
    "Nuevo":       {"color": "#5D9DF0", "fill": "#5D9DF0", "opacity": 0.9},
    "Contactado":  {"color": "#F5A524", "fill": "#F5A524", "opacity": 0.85},
    "Interesado":  {"color": "#A384F0", "fill": "#A384F0", "opacity": 0.9},
    "Cerrado":     {"color": "#46A758", "fill": "#46A758", "opacity": 0.95},
    "Descartado":  {"color": "#6B7485", "fill": "#6B7485", "opacity": 0.5},
    "Sin WhatsApp": {"color": "#6B7485", "fill": "#6B7485", "opacity": 0.5},
}

COUNTRY_CODES = {
    "Colombia": "57", "España": "34", "México": "52", "Argentina": "54",
    "Chile": "56", "Perú": "51", "Ecuador": "593", "Venezuela": "58",
    "Estados Unidos": "1", "Panamá": "507",
}

NICHO_SYNONYMS = {
    "Empresas locales": ["negocios locales", "empresa local", "comercio local"],
    "Servicios profesionales": ["profesionales independientes", "prestadores de servicios"],
    # ── Salud & Medicina ──
    "IPS de Salud (con Gerencia)": ["IPS", "gerencia de IPS", "administración servicios de salud", "dirección médica", "sede administrativa IPS"],
    "Hospitales y Clínicas": ["hospital privado", "clínica médica", "centro médico", "centro de especialistas", "hospital universitario"],
    "Odontólogos": ["clínica odontológica", "dentista", "centro odontológico", "odontología estética", "implantes dentales", "ortodoncia"],
    "Laboratorios Clínicos": ["laboratorio clínico", "laboratorio de análisis médicos", "laboratorio de patología", "toma de muestras laboratorio", "laboratorio imagenología"],
    "Farmacias y Droguerías": ["farmacia", "droguería", "farmacia 24 horas", "farmacia homeopática"],
    "Medicina Estética": ["medicina estética", "centro de estética facial", "tratamientos estéticos", "cosmiatría", "estética corporal"],
    "Clínicas de Cirugía Estética": ["clínica de cirugía plástica", "cirujano plástico", "centro de cirugía estética"],
    "Psicólogos": ["psicólogo", "consultorio de psicología", "centro psicológico", "terapia psicológica", "psicología clínica"],
    "Fisioterapeutas": ["fisioterapia", "centro de rehabilitación física", "terapia física", "rehabilitación deportiva"],
    "Ópticas": ["óptica", "optometría", "laboratorio óptico", "gafas y lentes"],
    "Salud Ocupacional": ["salud ocupacional", "medicina laboral", "riesgos laborales", "exámenes ocupacionales", "empresa de salud ocupacional"],
    "Dermatólogos": ["dermatología", "clínica estética", "dermatólogo"],
    "Ginecólogos": ["ginecología", "ginecólogo", "consultorio ginecológico"],
    "Pediatras": ["pediatría", "médico pediatra", "consultorio pediátrico"],
    "Veterinarias": ["clínica veterinaria", "veterinario", "hospital veterinario", "centro veterinario"],
    # ── Gastronomía & Ocio ──
    "Restaurantes": ["restaurante", "restaurante familiar", "restaurante con servicio a la mesa", "restaurante de mariscos", "restaurante de carnes"],
    "Cafeterías": ["cafetería", "café de especialidad", "coffee shop", "cafetería y repostería", "café brunch"],
    "Pizzerías": ["pizzería", "pizza", "pizzeria"],
    "Hamburgueserías": ["hamburguesería", "hamburguesas", "burger"],
    "Panaderías y Reposterías": ["panadería", "pastelería", "repostería", "panadería artesanal", "tortas y postres"],
    "Bares y Pubs": ["bar", "pub", "taberna", "cantina", "gastrobar", "cervecería"],
    "Sushi": ["sushi", "restaurante japonés", "sushi bar"],
    "Comida Vegana": ["restaurante vegano", "restaurante vegetariano", "comida saludable", "comida orgánica"],
    "Heladerías": ["heladería", "helados artesanales", "paletería", "yogurt helado"],
    "Catering": ["servicio de catering", "catering para eventos", "buffet empresarial", "alimentación empresarial"],
    "Comida Rápida": ["comida rápida", "asadero de pollo", "comidas rápidas y domicilios", "hamburguesería", "pizzería"],
    # ── Automotriz ──
    "Talleres Mecánicos": ["taller mecánico", "mecánica automotriz", "taller de carros", "mantenimiento de vehículos"],
    "Concesionarios": ["concesionario de carros", "venta de carros", "agencia de autos", "concesionario multimarca"],
    "Venta de Repuestos": ["venta de repuestos", "autopartes", "repuestos para carros", "distribuidora de autopartes"],
    "Lavado y Detailing": ["lavado de autos", "autolavado", "car wash", "detailing automotriz", "estética vehicular"],
    "Venta de Llantas": ["venta de llantas", "llantería", "centro de servicio llantas", "llantas y rines"],
    "Centros de Diagnóstico": ["centro de diagnóstico automotriz", "alineación y balanceo", "diagnóstico vehicular"],
    "Motos": ["venta de motos", "concesionario de motos", "taller de motos", "repuestos para motos"],
    "Grúas y Remolques": ["servicio de grúa", "remolque de vehículos", "grúas 24 horas", "asistencia en carretera"],
    # ── Construcción & Hogar ──
    "Inmobiliarias": ["inmobiliaria", "bienes raíces", "finca raíz", "agencia inmobiliaria", "arrendamientos y ventas"],
    "Arquitectos": ["estudio de arquitectura", "arquitecto", "diseño arquitectónico", "arquitectura e interiorismo"],
    "Ingeniería Civil": ["empresa de ingeniería civil", "consultoría de ingeniería", "obras civiles", "interventoría de obras"],
    "Constructoras": ["constructora", "ingeniería y construcción", "proyectos de vivienda", "empresa constructora"],
    "Ferreterías": ["ferretería", "ferretería mayorista", "depósito de materiales construcción", "ferretería industrial"],
    "Reformas y Remodelaciones": ["remodelaciones", "reformas de vivienda", "remodelación de cocinas", "remodelación de baños"],
    "Cerrajeros": ["cerrajería", "cerrajero 24 horas", "apertura de puertas", "cambio de cerraduras"],
    "Mueblerías": ["fábrica de muebles", "mueblería", "muebles a medida", "venta de muebles", "colchonería"],
    "Pintores y Acabados": ["pintor de casas", "servicio de pintura", "pintura de edificios", "drywall", "estucos y fachadas"],
    "Electricistas": ["electricista", "instalaciones eléctricas", "mantenimiento eléctrico", "instalación de paneles solares"],
    "Plomería": ["plomería", "fontanería", "plomero 24 horas", "reparación de fugas", "servicios hidrosanitarios"],
    "Administración de Propiedad Horizontal": ["administración de propiedad horizontal", "administración de edificios", "administración de conjuntos", "administrador de copropiedades"],
    # ── Belleza & Bienestar ──
    "Peluquerías": ["peluquería", "salón de belleza", "estilista", "salón de peinados"],
    "Barberías": ["barbería", "barbero", "barber shop", "corte de cabello"],
    "Spas y Masajes": ["spa", "centro de bienestar", "masajes", "spa de relajación", "baños de vapor"],
    "Centros de Uñas": ["centro de uñas", "manicure y pedicure", "uñas acrílicas", "nail art"],
    "Gimnasios": ["gimnasio", "centro de fitness", "crossfit", "entrenamiento funcional", "gym"],
    "Canchas Sintéticas": ["cancha sintética", "cancha de fútbol sintética", "alquiler de canchas", "fútbol 5"],
    "Yoga y Pilates": ["estudio de yoga", "pilates", "yoga studio", "yoga y meditación"],
    "Tatuajes": ["estudio de tatuajes", "tatuador", "piercing", "tattoo studio"],
    "Centros de Estética": ["centro de estética", "spa facial", "clínica de belleza", "tratamientos corporales"],
    # ── Profesionales & Legal ──
    "Abogados": ["firma de abogados", "bufete de abogados", "asesoría jurídica", "consultorio jurídico"],
    "Contadores": ["firma contable", "oficina de contadores", "revisoría fiscal", "auditoría contable"],
    "Notarías": ["notaría", "notaría pública", "trámites notariales", "autenticación de documentos"],
    "Asesores Fiscales": ["asesoría tributaria", "asesor fiscal", "impuestos y declaraciones", "consultoría fiscal"],
    "Agencias de Seguros": ["agencia de seguros", "asesoría de seguros", "corredor de seguros", "seguros empresariales"],
    "Agencias de Marketing": ["agencia de marketing digital", "agencia de publicidad", "marketing digital", "agencia de branding"],
    "Consultoría Empresarial": ["consultoría empresarial", "consultoría de gestión", "consultoría estratégica", "consultores de negocios"],
    "Recursos Humanos": ["empresa de recursos humanos", "outsourcing de personal", "selección de personal", "consultoría de talento humano"],
    # ── Industrial & Técnico ──
    "Fábricas y Manufactura": ["fábrica", "planta de producción", "manufactura", "planta industrial"],
    "Metalmecánica": ["metalmecánica", "fábrica de estructuras metálicas", "torneado y fresado", "soldadura industrial", "maquinado CNC"],
    "Plásticos y Empaques": ["fábrica de plásticos", "inyección de plástico", "empaques industriales", "envases plásticos"],
    "Químicos y Pinturas": ["fábrica de pinturas", "productos químicos industriales", "fábrica de jabones", "productos de aseo industrial"],
    "Textiles": ["fábrica textil", "hilandería", "tejeduría", "telas y tejidos"],
    "Imprentas": ["imprenta", "litografía", "impresión digital", "impresión offset"],
    "Logística y Bodegas": ["empresa de logística", "transporte de carga", "operador logístico", "bodegaje", "bodega de almacenamiento"],
    "Mantenimiento": ["mantenimiento industrial", "mantenimiento de plantas", "mantenimiento de edificios", "servicios del hogar"],
    "Control de Plagas": ["control de plagas", "fumigación", "control de roedores", "desinsectación"],
    "Maquinaria Pesada": ["alquiler maquinaria pesada", "retroexcavadoras alquiler", "maquinaria construcción", "grúas alquiler"],
    # ── Educación ──
    "Colegios": ["colegio privado", "institución educativa privada", "colegio bilingüe", "liceo", "gimnasio escolar"],
    "Jardines Infantiles": ["jardín infantil", "preescolar", "guardería", "centro de desarrollo infantil"],
    "Academias de Idiomas": ["academia de idiomas", "clases de inglés", "escuela de idiomas", "centro de idiomas"],
    "Universidades": ["universidad", "institución universitaria", "centro de educación superior", "universidad tecnológica"],
    "Formación Técnica": ["centro de formación técnica", "instituto técnico", "cursos técnicos", "formación para el trabajo"],
    "Escuelas de Conducción": ["escuela de conducción", "autoescuela", "clases de manejo", "escuela de manejo"],
    # ── Tecnología ──
    "Reparación de Celulares": ["reparación de celulares", "servicio técnico celulares", "cambio de pantalla", "reparación de smartphones"],
    "Soporte Técnico": ["soporte técnico de computadores", "servicio técnico de PC", "mantenimiento de computadores", "soporte informático empresarial"],
    "Desarrollo Web": ["empresa de software", "desarrollo web y móvil", "páginas web", "diseño web", "casa de software"],
    "Venta de Electrónica": ["venta de electrónica", "tienda de tecnología", "computadores y accesorios", "tienda de electrónica"],
    "CCTV y Seguridad Electrónica": ["instalación de cámaras de seguridad", "CCTV", "circuito cerrado de televisión", "videovigilancia", "control de acceso"],
    "Telecomunicaciones e Internet": ["proveedor de internet", "empresa de telecomunicaciones", "internet fibra óptica", "internet empresarial"],
    # ── Moda & Retail ──
    "Tiendas de Ropa": ["tienda de ropa", "boutique", "ropa de moda", "tienda de vestuario"],
    "Zapaterías": ["zapatería", "venta de calzado", "calzado deportivo", "tienda de zapatos"],
    "Joyerías": ["joyería", "bisutería", "venta de joyas", "relojería"],
    "Supermercados": ["supermercado", "mercado", "minimercado", "supermercado mayorista"],
    "Tiendas Deportivas": ["tienda deportiva", "artículos deportivos", "tienda de deportes", "bicicletas y deportes"],
    "Cosméticos y Perfumerías": ["tienda de cosméticos", "perfumería", "venta de cosméticos", "productos de belleza"],
    # ── Mascotas ──
    "Peluquería Canina": ["peluquería canina", "dog grooming", "peluquería para perros", "estética canina"],
    "Tiendas de Mascotas": ["tienda de mascotas", "pet shop", "accesorios para mascotas", "alimentos para mascotas"],
    # ── Eventos & Turismo ──
    "Hoteles": ["hotel", "hospedaje", "hostal", "hotel centro"],
    "Hoteles Boutique": ["hotel boutique", "hostal de lujo", "glamping de lujo", "hotel con encanto"],
    "Salones de Eventos": ["salón de eventos", "salón de fiestas", "salón de recepciones", "centro de eventos"],
    "Fotógrafos": ["fotógrafo profesional", "estudio fotográfico", "fotografía de eventos", "video profesional"],
    "Agencias de Viajes": ["agencia de viajes", "operador turístico", "agencia de turismo", "tours"],
    "Organización de Eventos": ["organización de eventos", "eventos corporativos", "producción de eventos", "coordinación de eventos"],
    "Turismo de Aventura": ["turismo de aventura", "ecoturismo", "parapente", "rafting", "turismo rural"],
    # ── Servicios Empresariales ──
    "Seguridad Privada": ["empresa seguridad privada", "vigilancia y seguridad", "escoltas", "empresa de vigilancia"],
    "Mensajería y Paquetería": ["servicio de mensajería", "mensajería empresarial", "paquetería", "servicio de domicilios"],
    "Mudanzas y Fletes": ["mudanzas", "fletes", "empresa de mudanzas", "transporte de mudanzas"],
    "Limpieza Industrial": ["limpieza industrial", "aseo y mantenimiento empresas", "limpieza de fachadas", "desinfección industrial"],
    # ── Aguas & Ambiental ──
    "Plantas de Tratamiento de Aguas": ["PTAR", "tratamiento aguas industriales", "planta tratamiento aguas residuales"],
    "Transporte de Aguas Residuales": ["transporte de aguas residuales", "carrotanques de aguas", "transporte de residuos líquidos"],
    "Succión de Pozos Sépticos": ["succión de pozos sépticos", "limpieza de pozos sépticos", "vactor"],
    "Servicios de Vactor": ["servicio de vactor", "succión de lodos", "limpieza de alcantarillado"],
    "Ingeniería Ambiental": ["consultoría ambiental", "ingeniería ambiental", "estudios de impacto ambiental", "gestión ambiental empresarial"],
    "Reciclaje y Residuos": ["empresa de reciclaje", "reciclaje de residuos", "centro de acopio", "gestión de residuos"],
    "Energías Renovables": ["instalación de paneles solares", "energía solar", "energías renovables", "instalación solar fotovoltaica"],
    # ── Agroindustria ──
    "Ganadería y Lecherías": ["ganadería lechera", "finca lechera", "acopio de leche", "cooperativa lechera"],
    "Fincas Cafeteras": ["finca cafetera", "productor de café", "beneficiadero café", "café especial origen", "tostadora de café"],
    "Flores y Exportación": ["cultivo de flores", "exportadora de flores", "comercializadora internacional flores", "invernadero de flores"],
    "Cultivos Agrícolas": ["cultivo de frutas", "plantación agrícola", "productor agrícola", "finca de aguacate", "productor de hortalizas"],
    "Insumos Agrícolas": ["venta de insumos agrícolas", "agroquímicos", "fertilizantes", "semillas y abonos", "tienda agropecuaria"],
    "Maquinaria Agrícola": ["venta de tractores", "maquinaria agrícola", "implementos agrícolas", "alquiler de maquinaria agrícola"],
    # ── Alimentos & Bebidas ──
    "Embutidos y Cárnicos": ["planta embutidos", "fábrica embutidos", "procesadora cárnica", "frigorífico", "distribuidora de carnes"],
    "Fábricas de Snacks": ["fábrica snacks", "procesadora alimentos", "frituras industriales", "platanitos industrial"],
    "Panaderías Industriales": ["panadería industrial", "fábrica de pan", "distribuidora de pan", "panificación industrial"],
    "Bebidas y Licores": ["productora de bebidas", "fábrica de jugos", "embotelladora", "destilería", "cervecería artesanal"],
    "Distribuidoras de Alimentos": ["distribuidora de alimentos", "comercializadora de víveres", "alimentos al por mayor", "mayorista de alimentos"],
    # ── Finanzas ──
    "Asesorías Financieras": ["asesoría financiera", "consultoría financiera", "asesor de inversiones", "planeación financiera", "factoring"],
    # ── Deportes ──
    "Centros Deportivos": ["centro deportivo", "club deportivo", "cancha de fútbol", "polideportivo", "piscina pública"],
    "Academias Deportivas": ["escuela de fútbol", "academia de natación", "escuela de tenis", "academia de artes marciales"],
    # ── Medios ──
    "Medios de Comunicación": ["emisora de radio", "canal de televisión", "periódico digital", "medio de comunicación", "productora audiovisual"],
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
    "abogados": "Página web profesional y chatbot para consultas, agenda de citas y seguimiento de casos.",
    "contadores": "Portal para clientes con envío de documentos, chatbot de consultas y recordatorios de vencimientos.",
    "odontologos": "Agenda digital de citas, recordatorios por WhatsApp y chatbot para primeras consultas.",
    "veterinarias": "Agenda de citas, recordatorios de vacunas y chatbot para consultas frecuentes.",
    "hoteles": "Página web con reservas en línea, motor de tarifas y chatbot de atención 24/7.",
    "agencias de viajes": "Página web de paquetes, cotizador en línea y chatbot para asesoría.",
    "salones de eventos": "Página web con galería, cotizador de paquetes y chatbot para reservas.",
    "spas": "Sistema de reservas, membresías y recordatorios de citas por WhatsApp.",
    "centros de estetica": "Agenda de citas, CRM de pacientes y chatbot para valoraciones.",
    "farmacias": "Sistema de domicilios, chatbot de pedidos y recordatorios de recetas.",
    "clinicas medicas": "Agenda de citas en línea, recordatorios y portal de pacientes.",
    "psicologos": "Agenda de sesiones, recordatorios por WhatsApp y portal para pacientes.",
    "fisioterapeutas": "Sistema de citas, planes de tratamiento y recordatorios automáticos.",
    "supermercados": "Catálogo y domicilios en línea con chatbot para pedidos rápidos.",
    "tiendas de ropa": "Tienda virtual con catálogo, tallas y pedidos por WhatsApp.",
    "zapaterias": "Catálogo en línea con envíos y chatbot para consultas de tallas y stock.",
    "peluquerias": "Agenda de citas, recordatorios por WhatsApp y membresías de fidelización.",
    "panaderias": "Pedidos anticipados en línea y chatbot para domicilios recurrentes.",
    "motos": "Sistema de cotizaciones, agenda de mantenimiento y recordatorios de servicios.",
    "concesionarios": "CRM comercial, cotizador en línea y chatbot para citas de prueba de manejo.",
    "ferreterias": "Catálogo en línea, cotizaciones por WhatsApp y programa de clientes frecuentes.",
    "mueblerias": "Catálogo virtual con medidas a medida y cotizador por WhatsApp.",
    "agencia de marketing": "Software de gestión de clientes, reportes automatizados y portal de resultados.",
    "seguridad privada": "Sistema de gestión de guardias, reportes digitales y portal para clientes.",
    "logistica": "Plataforma de seguimiento de envíos, reportes de entregas y portal de clientes.",
    "distribuidora de alimentos": "Plataforma de pedidos B2B, seguimiento de entregas y facturación automatizada.",
    "fabricas": "ERP ligero a medida, control de producción e indicadores en tiempo real.",
    "empresas de software": "Automatización de procesos internos y mejoras de producto.",
    "hoteles boutique": "Página web elegante con reservas directas y chatbot de concierge.",
    "gimnasios": "Sistema de membresías, reservas de clases y chatbot para captar nuevos inscritos.",
    "opticas": "Agenda de exámenes, recordatorios y catálogo de lentes en línea.",
    "notarias": "Agendamiento de trámites en línea, recordatorios y seguimiento de documentos.",
    "agencias de seguros": "CRM de pólizas, recordatorios de vencimientos y cotizador en línea.",
    "reparacion de celulares": "Sistema de órdenes de servicio, seguimiento por WhatsApp y cobros.",
    "cctv": "Página web de servicios, cotizador de proyectos y chatbot de consultas.",
    "imprentas": "Cotizador en línea, pedidos recurrentes y portal para clientes corporativos.",
    "mudanzas": "Cotizador de mudanzas, seguimiento de servicios y reservas en línea.",
    "reciclaje": "Sistema de programación de recolecciones y portal para clientes empresariales.",
    "energias renovables": "Cotizador de proyectos solares, cálculo de ahorro y CRM comercial.",
    "consultoria empresarial": "Portal de diagnóstico, reportes automatizados y seguimiento de planes.",
    "recursos humanos": "Plataforma de selección, pruebas en línea y portal de vacantes.",
    "control de plagas": "Sistema de contratos recurrentes, recordatorios de fumigación y reportes.",
    "telecomunicaciones": "Plataforma de clientes, facturación automática y soporte por chatbot.",
    "escuelas de conduccion": "Agenda de clases, seguimiento de estudiantes y recordatorios de exámenes.",
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