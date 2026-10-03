import unicodedata
from typing import Literal

EstadoValidacion = Literal["valida", "votacion", "invalida"]


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.strip().upper())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Diccionario local para las categorías que pueden validarse automáticamente.
# En NOMBRE usamos una lista amplia de nombres habituales como primera capa.
# Si un nombre no está aquí pero respeta la letra de la ronda, NO se rechaza:
# pasa a votación para que los jugadores decidan.
DICCIONARIO_NOMBRES = {
    "A": ["ANDRES", "ANDRÉS", "ALEJANDRO", "ALEJANDRA", "ANA", "ANA MARIA", "ANDREA", "ANTONIO", "ANGELA", "ANGEL", "ANGELICA", "ARIEL", "ARTURO", "ALBERTO", "ALFONSO", "ALICIA", "AMANDA", "ADRIANA", "ADRIAN", "ALEX", "ALEXANDER", "ALEXANDRA", "ALAN", "ALANNA", "ARMANDO", "AURELIO", "AURELIANO", "ABIGAIL", "ADAM", "ADAN"],
    "B": ["BRAYAN", "BRYAN", "BRUNO", "BEATRIZ", "BRENDA", "BLANCA", "BENJAMIN", "BENJAMÍN", "BIBIANA", "BERNARDO", "BERTA", "BELEN", "BELÉN", "BETO", "BETTY", "BORIS"],
    "C": ["CARLOS", "CARLA", "CAMILO", "CAMILA", "CRISTIAN", "CRISTINA", "CLAUDIA", "CARMEN", "CECILIA", "CESAR", "CÉSAR", "CATALINA", "CAROLINA", "CAROL", "CAROLINA", "CLAUDIO", "CONRADO"],
    "D": ["DANIEL", "DANIELA", "DAVID", "DIANA", "DIEGO", "DORIS", "DARIO", "DARÍO", "DULCE", "DOMINGO", "DANILO", "DEBORA", "DÉBORA", "DAMIÁN", "DAMIAN"],
    "E": ["EDUARDO", "ELENA", "ELISA", "ELIZABETH", "EMILIO", "EMILIA", "ENRIQUE", "ESTEBAN", "ESTEFANIA", "ESTEFANÍA", "ERIKA", "ERICK", "ERNESTO", "EVA", "EUGENIO"],
    "F": ["FERNANDO", "FELIPE", "FABIANA", "FABIAN", "FABIÁN", "FATIMA", "FÁTIMA", "FRANCISCO", "FRANCISCA", "FELIX", "FÉLIX", "FLORENCIA", "FEDERICO", "FREDY", "FREDDY"],
    "G": ["GABRIEL", "GABRIELA", "GUSTAVO", "GLORIA", "GERARDO", "GENESIS", "GÉNESIS", "GISELA", "GUILLERMO", "GREGORIO", "GABRIELA", "GILBERTO"],
    "H": ["HECTOR", "HÉCTOR", "HELENA", "HERNAN", "HERNÁN", "HUGO", "HORACIO", "HILDA", "HUMBERTO", "HANS"],
    "I": ["IVAN", "IVÁN", "ISABEL", "ISABELA", "ISABELLA", "IRENE", "IGNACIO", "INES", "INÉS", "IRMA", "ISAAC", "ISMAEL"],
    "J": ["JUAN", "JUANA", "JOSE", "JOSÉ", "JOSEFA", "JULIO", "JULIA", "JULIAN", "JULIÁN", "JULIANA", "JORGE", "JAVIER", "JESSICA", "JESUS", "JESÚS", "JOHAN", "JOHANA", "JHON", "JOHN", "JONATHAN", "JIMENA", "JIMMY"],
    "K": ["KAREN", "KARLA", "KARINA", "KEVIN", "KENNETH", "KELLY", "KIMBERLY", "KATHERINE", "KATIA", "KAROL"],
    "L": ["LUIS", "LUISA", "LINA", "LAURA", "LEONARDO", "LEONEL", "LEONOR", "LILIANA", "LUCIA", "LUCÍA", "LUZ", "LORENA", "LORETO", "LUCAS", "LUCAS", "LINA MARIA", "LINA MARÍA", "LILI", "LORENA"],
    "M": ["MARIA", "MARÍA", "MARIO", "MIGUEL", "MICHAEL", "MATEO", "MATIAS", "MATÍAS", "MARTIN", "MARTÍN", "MANUEL", "MANUELA", "MARCOS", "MARCO", "MARCELA", "MARGARITA", "MARTA", "MAURICIO", "MAURICIO", "MELISSA", "MELINA", "MÓNICA", "MONICA", "MARIANA", "MARIANA", "MAXIMILIANO", "MAXIMILIAN", "MILENA"],
    "N": ["NICOLAS", "NICOLÁS", "NATALIA", "NATALY", "NORA", "NOEL", "NORMA", "NESTOR", "NÉSTOR", "NAOMI", "NICOLE"],
    "O": ["OSCAR", "ÓSCAR", "OLGA", "OMAR", "ORLANDO", "OLIVER", "OCTAVIO", "OFELIA", "OSVALDO"],
    "P": ["PABLO", "PAOLA", "PATRICIA", "PATRICIO", "PEDRO", "PAULA", "PEPE", "PILAR", "PRISCILA", "PENELOPE", "PENÉLOPE", "PHILIP", "PHILLIP", "PHILIPPE"],
    "Q": ["QUINTIN", "QUINTÍN", "QUITERIA"],
    "R": ["RAFAEL", "RAQUEL", "RAMON", "RAMÓN", "ROBERTO", "ROSA", "RODRIGO", "RICARDO", "REBECA", "REBECCA", "ROMAN", "ROMÁN", "RUBEN", "RUBÉN", "ROXANA", "ROXANNA", "RENATO", "RENATA", "RITA", "ROLANDO"],
    "S": ["SANTIAGO", "SEBASTIAN", "SEBASTIÁN", "SARA", "SOFIA", "SOFÍA", "SAMUEL", "SANDRA", "SERGIO", "SILVIA", "SIMON", "SIMÓN", "SUSANA", "SALVADOR", "SILVANA", "SONIA", "SUSY"],
    "T": ["TATIANA", "TATIANA", "TOMAS", "TOMÁS", "THOMAS", "THIAGO", "TATIANA", "TERESA", "TERESITA", "TIMOTEO", "TITO", "TRIANA"],
    "U": ["ULISES", "URSULA", "ÚRSULA", "URIEL"],
    "V": ["VALENTINA", "VALERIA", "VALERIO", "VICTOR", "VÍCTOR", "VICTORIA", "VERONICA", "VERÓNICA", "VIVIANA", "VICENTE", "VIOLETA"],
    "W": ["WALTER", "WILLIAM", "WILFRIDO", "WILSON", "WENDY", "WENDY", "WILMER", "WINSTON", "WENDY"],
    "X": ["XIMENA", "XIMENA", "XAVIER", "XAVIERA"],
    "Y": ["YULIANA", "YULY", "YESSICA", "YESENIA", "YERSON", "YASMIN", "YASMÍN"],
    "Z": ["ZOE", "ZOE", "ZULEMA", "ZULMA", "ZACARIAS", "ZACARÍAS", "ZENOBIA"],
}

DICCIONARIO_CATEGORIAS = {
    "apellido": {
        "A": ["ALVAREZ", "ACOSTA", "ARIAS", "AGUILAR", "ARBOLEDA", "AGUDELO"],
        "B": ["BERMUDEZ", "BLANCO", "BUITRAGO", "BARRIOS", "BOLIVAR", "BUSTAMANTE"],
        "C": ["CAMACHO", "CARRANZA", "CASTRO", "CARDONA", "CORTES", "CRUZ"],
        "D": ["DIAZ", "DUQUE", "DELGADO", "DOMINGUEZ", "DURAN", "DUARTE"],
        "E": ["ESPINOSA", "ESCOBAR", "ESTRADA", "ECHEVARRIA", "ENRIQUEZ"],
        "F": ["FERNANDEZ", "FLOREZ", "FRANCO", "FUENTES", "FIGUEROA", "FAJARDO"],
        "G": ["GARCIA", "GOMEZ", "GONZALEZ", "GUTIERREZ", "GIRALDO", "GUZMAN"],
        "L": ["LOPEZ", "LONDOÑO", "LARA", "LEON", "LOZANO", "LUNA"],
        "M": ["MARTINEZ", "MEDINA", "MORALES", "MENDOZA", "MEJIA", "MONTOYA"],
        "P": ["PEREZ", "PEÑA", "PINEDA", "PARRA", "PALACIOS", "PATIÑO"],
        "R": ["RODRIGUEZ", "RAMIREZ", "RESTREPO", "REYES", "RIVERA", "ROJAS"],
        "S": ["SANCHEZ", "SUAREZ", "SALAZAR", "SIERRA", "SILVA", "SOTO"],
        "T": ["TORRES", "TRUJILLO", "TOBON", "TAPIA", "TELLO"],
        "V": ["VARGAS", "VASQUEZ", "VALENCIA", "VEGA", "VILLA", "VILLAMIZAR"],
    },
    "ciudad": {
        "A": ["ARMENIA", "ARAUCA", "AMSTERDAM", "AREQUIPA", "ASUNCION", "ATENAS"],
        "B": ["BOGOTA", "BARRANQUILLA", "BUCARAMANGA", "BUENAVENTURA", "BARCELONA", "BERLIN"],
        "C": ["CALI", "CARTAGENA", "CUCUTA", "CARACAS", "CHICAGO", "CUENCA"],
        "D": ["DUITAMA", "DOSQUEBRADAS", "DALLAS", "DUBLIN", "DENVER", "DETROIT"],
        "E": ["ENVIGADO", "ESPINAL", "ESTAMBUL", "EDIMBURGO"],
        "F": ["FLORENCIA", "FACATATIVA", "FILADELFIA", "FRANKFURT"],
        "G": ["GIRARDOT", "GUADALAJARA", "GUATEMALA", "GINEBRA", "GRANADA"],
        "L": ["LETICIA", "LIMA", "LONDRES", "LISBOA", "LOS ANGELES", "LA PAZ"],
        "M": ["MEDELLIN", "MONTERIA", "MANIZALES", "MADRID", "MIAMI", "MEXICO"],
        "P": ["PEREIRA", "PASTO", "POPAYAN", "PANAMA", "PARIS", "PRAGA"],
        "R": ["RIOHACHA", "ROMA", "RIO DE JANEIRO", "ROSARIO", "RABAT"],
        "S": ["SANTA MARTA", "SINCELEJO", "SOACHA", "SANTIAGO", "SEVILLA"],
        "T": ["TUNJA", "TULUA", "TOLUCA", "TORONTO", "TOKIO"],
        "V": ["VILLAVICENCIO", "VALLEDUPAR", "VALENCIA", "VIENA", "VENECIA"],
    },
    "fruta": {
        "A": ["ARANDANO", "ANON", "AGUACATE", "ALBARICOQUE", "ANANA"],
        "B": ["BANANO", "BANANA", "BOROJO", "BADEA", "BREVA"],
        "C": ["CEREZA", "CIRUELA", "COCO", "CHIRIMOYA", "CURUBA"],
        "D": ["DURAZNO", "DATIL", "DAMASCO"],
        "E": ["ENDRIÑA", "ENEBRO", "ESCARAMUJO"],
        "F": ["FRESA", "FRAMBUESA", "FRUTILLA", "FEIJOA"],
        "G": ["GRANADILLA", "GUANABANA", "GUAYABA", "GROSELLA", "GRANADA"],
        "L": ["LIMON", "LIMA", "LULO", "LICHI"],
        "M": ["MANGO", "MANZANA", "MELON", "MANDARINA", "MORA", "MARACUYA"],
        "P": ["PAPAYA", "PIÑA", "PLATANO", "PERA", "POMELO"],
        "R": ["RAMBUTAN", "RED CURRANT", "RUIPONCE"],
        "S": ["SANDIA", "SAUCO", "SAPOTE"],
        "T": ["TOMATE DE ARBOL", "TAMARINDO", "TANGERINA", "TORONJA"],
        "V": ["VAINILLA", "VERDE LIMON", "VID"],
    },
    "animal": {
        "A": ["AGUILA", "ARAÑA", "ABEJA", "AVESTRUZ", "ANTILOPE", "ARDILLA"],
        "B": ["BALLENA", "BUFALO", "BUHO", "BURRO", "BUEY", "BABUINO"],
        "C": ["CABALLO", "CABRA", "CAMELLO", "CANARIO", "CANGURO", "CEBRA"],
        "D": ["DELFIN", "DINOSAURIO", "DROMEDARIO", "DINGO"],
        "E": ["ELEFANTE", "ERIZO", "ESCORPION", "ESCARABAJO"],
        "F": ["FLAMENCO", "FOCA", "FERRET", "FALCON"],
        "G": ["GATO", "GALLINA", "GALLO", "GOLONDRINA", "GORILA", "GUEPARDO"],
        "L": ["LEON", "LEOPARDO", "LECHUZA", "LORO", "LOBO", "LLAMA"],
        "M": ["MONO", "MARIPOSA", "MURCIELAGO", "MOSCA", "MULA", "MOFETA", "MEDUSA"],
        "P": ["PERRO", "PATO", "PAVO", "PALOMA", "PANTERA", "PINGUINO"],
        "R": ["RATA", "RATON", "RINOCERONTE", "RANA", "RENO"],
        "S": ["SAPO", "SERPIENTE", "SALMON", "SURICATA"],
        "T": ["TIGRE", "TIBURON", "TORTUGA", "TOPO", "TUCAN"],
        "V": ["VACA", "VICUÑA", "VENADO", "VIBORA"],
    },
    "cosa": {
        "A": ["ANILLO", "AUTO", "AVION", "ALMOHADA", "ARMARIO", "ABANICO"],
        "B": ["BALON", "BARCO", "BOLIGRAFO", "BOTELLA", "BOTON", "BICICLETA"],
        "C": ["CAMA", "CAMISA", "CAMPANA", "CANDADO", "CARRO", "CUADERNO"],
        "D": ["DADO", "DISCO", "DIPLOMA", "DIAMANTE"],
        "E": ["ESPEJO", "ESCOBA", "ESCRITORIO", "ESCALERA", "ESPADA"],
        "F": ["FALDA", "FAROL", "FLECHA", "FLAUTA", "FOTO"],
        "G": ["GUITARRA", "GORRA", "GUANTE", "GOMA", "GRAPADORA"],
        "L": ["LAPIZ", "LAMPARA", "LAVADORA", "LIBRO", "LENTES"],
        "M": ["MESA", "MOTOR", "MARTILLO", "MONEDA", "MALETA", "MICROFONO"],
        "P": ["PAPEL", "PANTALON", "PALA", "PELOTA", "PIANO"],
        "R": ["RELOJ", "RADIO", "REGLA", "RUEDA", "ROPA"],
        "S": ["SILLA", "SOBRE", "SOMBRERO", "SARTEN", "SIERRA"],
        "T": ["TELEFONO", "TIJERAS", "TOALLA", "TORNILLO", "TAZA"],
        "V": ["VASO", "VENTANA", "VENTILADOR", "VESTIDO", "VELA"],
    },
}


def validar_palabra(categoria: str, palabra: str, letra: str) -> bool:
    """Compatibilidad con el código existente: solo devuelve si es automáticamente válida."""
    return evaluar_palabra(categoria, palabra, letra) == "valida"


def evaluar_palabra(categoria: str, palabra: str, letra: str) -> EstadoValidacion:
    """
    Determina el camino de validación de una respuesta.

    - invalida: vacía o no empieza por la letra de la ronda.
    - valida: reconocida automáticamente por el diccionario.
    - votacion: empieza por la letra, pero requiere validación humana.

    En Nombre usamos una lista amplia de nombres habituales para validar automáticamente.
    Si el nombre no está en esa lista pero comienza con la letra, pasa a votación.
    Así el diccionario ayuda al sistema sin impedir nombres poco comunes.
    """
    palabra_norm = normalizar(palabra)
    letra_norm = normalizar(letra)
    cat = normalizar(categoria).lower()

    if not palabra_norm or not letra_norm:
        return "invalida"

    if not palabra_norm.startswith(letra_norm):
        return "invalida"

    if cat == "nombre":
        lista_nombres = DICCIONARIO_NOMBRES.get(letra_norm, [])
        lista_norm = {normalizar(w) for w in lista_nombres}
        if palabra_norm in lista_norm:
            return "valida"
        return "votacion"

    lista_letra = DICCIONARIO_CATEGORIAS.get(cat, {}).get(letra_norm)
    if lista_letra:
        lista_norm = {normalizar(w) for w in lista_letra}
        if palabra_norm in lista_norm:
            return "valida"

    # Una respuesta que respeta la letra pero que el sistema no reconoce
    # nunca se descarta automáticamente: pasa a votación.
    return "votacion"
