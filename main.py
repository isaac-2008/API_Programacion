import logging
import os
import webbrowser
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
import json


logging.basicConfig(
    filename="app.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class FootballClient:

    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

    class APIConnectionError(Exception):
        pass

    class RecursoNoEncontrado(Exception):
        pass

    def _hacer_peticion(self, endpoint: str) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"

        peticion = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ProyectoPOO-Futbol/1.0)"
            },
        )

        try:
            with urlopen(peticion, timeout=8) as respuesta:
                contenido_bruto = respuesta.read()
                return json.loads(contenido_bruto)

        except HTTPError as error_http:
            if error_http.code == 404:
                logging.info("Sin resultados para %s", url)
                raise self.RecursoNoEncontrado(
                    "No se encontraron resultados para esa búsqueda."
                ) from error_http

            logging.error(
                "Error HTTP al consultar %s: %s",
                url,
                error_http
            )

            raise self.APIConnectionError(
                f"El servidor respondió con un error ({error_http.code})."
            ) from error_http

        except URLError as error_conexion:
            logging.error(
                "Error de conexión al consultar %s: %s",
                url,
                error_conexion
            )

            raise self.APIConnectionError(
                "No fue posible conectarse a la API. "
                "Verificá tu conexión a internet."
            ) from error_conexion

        except json.JSONDecodeError as error_json:
            logging.error(
                "Respuesta no es JSON válido: %s",
                error_json
            )

            raise self.APIConnectionError(
                "La API devolvió una respuesta malformada."
            ) from error_json

    def buscar_equipos_por_nombre(self, nombre: str) -> dict:
        return self._hacer_peticion(
            f"searchteams.php?t={quote(nombre)}"
        )

    def obtener_equipo_por_id(self, id_equipo: int) -> dict:
        return self._hacer_peticion(
            f"lookupteam.php?id={id_equipo}"
        )


class Team:

    def __init__(
        self,
        nombre,
        pais,
        liga,
        estadio,
        fundacion,
        escudo,
    ):
        self.nombre = nombre
        self.pais = pais
        self.liga = liga
        self.estadio = estadio
        self.fundacion = fundacion
        self.escudo = escudo

    @classmethod
    def from_json_data(cls, datos: dict) -> "Team":
        try:
            return cls(
                nombre=datos["strTeam"],
                pais=datos.get("strCountry", "Desconocido"),
                liga=datos.get("strLeague", "Desconocida"),
                estadio=datos.get("strStadium", "Desconocido"),
                fundacion=datos.get("intFormedYear", "Desconocido"),
                escudo=datos.get("strBadge", ""),
            )

        except KeyError as clave_faltante:
            logging.warning(
                "Campo faltante en el JSON del equipo: %s",
                clave_faltante
            )

            return cls(
                nombre=datos.get("strTeam", "Desconocido"),
                pais=datos.get("strCountry", "Desconocido"),
                liga=datos.get("strLeague", "Desconocida"),
                estadio=datos.get("strStadium", "Desconocido"),
                fundacion=datos.get("intFormedYear", "Desconocido"),
                escudo=datos.get("strBadge", ""),
            )

    def __str__(self) -> str:
        return (
            f"{self.nombre}\n"
            f"  País    : {self.pais}\n"
            f"  Liga    : {self.liga}\n"
            f"  Estadio : {self.estadio}\n"
            f"  Fundación: {self.fundacion}"
        )


class FootballService:

    def __init__(self, cliente: FootballClient):
        self._cliente = cliente

    def buscar_por_nombre(self, nombre: str) -> list:

        assert isinstance(nombre, str) and nombre.strip() != "", (
            "Precondición violada: el nombre del equipo no puede estar vacío."
        )

        try:
            datos_crudos = self._cliente.buscar_equipos_por_nombre(
                nombre.strip()
            )

        except FootballClient.RecursoNoEncontrado:
            return []

        except FootballClient.APIConnectionError as error_api:
            print(f"⚠️ {error_api}")
            return []

        resultados_json = datos_crudos.get("teams") or []

        equipos = [
            Team.from_json_data(item)
            for item in resultados_json
        ]

        assert isinstance(equipos, list), (
            "Postcondición violada: el servicio siempre debe devolver una lista."
        )

        return equipos

    def obtener_por_id(self, id_equipo: int) -> list:

        assert id_equipo >= 1, (
            "Precondición violada: el ID debe ser mayor o igual a 1."
        )

        try:
            datos_crudos = self._cliente.obtener_equipo_por_id(
                id_equipo
            )

        except FootballClient.RecursoNoEncontrado:
            return []

        except FootballClient.APIConnectionError as error_api:
            print(f"⚠️ {error_api}")
            return []

        resultados_json = datos_crudos.get("teams") or []

        equipos = [
            Team.from_json_data(item)
            for item in resultados_json
        ]

        assert isinstance(equipos, list), (
            "Postcondición violada: el servicio siempre debe devolver una lista."
        )

        return equipos


class ReporteHTML:

    RUTA_ARCHIVO = "reporte_equipos_futbol.html"

    _ESTILO_CSS = """
        body {
            font-family: Arial, sans-serif;
            background: #071a12;
            color: #eeeeee;
            padding: 2rem;
        }

        h1 {
            color: #55e878;
            text-align: center;
        }

        .fecha {
            text-align: center;
            color: #aaaaaa;
            margin-bottom: 2rem;
        }

        .grid {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 1.5rem;
        }

        .card {
            background: #10291e;
            border-radius: 12px;
            overflow: hidden;
            width: 260px;
            min-height: 360px;
            box-shadow: 0 4px 12px rgba(0,0,0,.5);
            transition: transform .2s;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .card img {
            width: 100%;
            height: 220px;
            object-fit: contain;
            background: #ffffff;
            display: block;
        }

        .card .info {
            padding: 1rem;
        }

        .card h2 {
            font-size: 1.2rem;
            margin: .2rem 0 .8rem;
            color: #55e878;
        }

        .card p {
            font-size: .9rem;
            margin: .4rem 0;
            color: #cccccc;
        }

        .etiqueta {
            color: #ffffff;
            font-weight: bold;
        }

        .vacio {
            color: #e0c463;
            text-align: center;
            font-size: 1.2rem;
        }
    """

    def _tarjeta_html(self, equipo: Team) -> str:

        imagen = equipo.escudo

        if not imagen:
            imagen = (
                "https://via.placeholder.com/260x220"
                "?text=Sin+escudo"
            )

        return f"""
        <div class="card">

            <img
                src="{imagen}"
                alt="Escudo de {equipo.nombre}"
            >

            <div class="info">

                <h2>{equipo.nombre}</h2>

                <p>
                    <span class="etiqueta">País:</span>
                    {equipo.pais}
                </p>

                <p>
                    <span class="etiqueta">Liga:</span>
                    {equipo.liga}
                </p>

                <p>
                    <span class="etiqueta">Estadio:</span>
                    {equipo.estadio}
                </p>

                <p>
                    <span class="etiqueta">Fundación:</span>
                    {equipo.fundacion}
                </p>

            </div>

        </div>
        """

    def generar_y_abrir(
        self,
        equipos: list,
        titulo: str = "Equipos de Fútbol"
    ) -> None:

        if equipos:

            tarjetas = "".join(
                self._tarjeta_html(equipo)
                for equipo in equipos
            )

            cuerpo = f"""
                <div class="grid">
                    {tarjetas}
                </div>
            """

        else:

            cuerpo = """
                <p class="vacio">
                    No se encontraron equipos.
                </p>
            """

        html = f"""
        <!DOCTYPE html>

        <html lang="es">

        <head>

            <meta charset="UTF-8">

            <title>
                {titulo} - Fútbol
            </title>

            <style>
                {self._ESTILO_CSS}
            </style>

        </head>

        <body>

            <h1>{titulo}</h1>

            <p class="fecha">
                Generado el
                {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </p>

            {cuerpo}

        </body>

        </html>
        """

        with open(
            self.RUTA_ARCHIVO,
            "w",
            encoding="utf-8"
        ) as archivo:

            archivo.write(html)

        ruta_absoluta = os.path.abspath(
            self.RUTA_ARCHIVO
        )

        webbrowser.open(
            f"file://{ruta_absoluta}"
        )


class MenuInteractivo:

    def __init__(
        self,
        servicio: FootballService,
        reporte: ReporteHTML
    ):
        self._servicio = servicio
        self._reporte = reporte

    def _mostrar_resultados(
        self,
        equipos: list,
        titulo: str
    ) -> None:

        self._reporte.generar_y_abrir(
            equipos,
            titulo
        )

        cantidad = len(equipos)

        print(
            f"✅ Se generó la página con "
            f"{cantidad} equipo(s). "
            f"Se abrió en tu navegador.\n"
        )

    def _opcion_buscar(self) -> None:

        nombre = input(
            "Ingresá el nombre del equipo: "
        )

        if not nombre.strip():
            print(
                "⚠️ El nombre no puede estar vacío.\n"
            )
            return

        resultados = self._servicio.buscar_por_nombre(
            nombre
        )

        self._mostrar_resultados(
            resultados,
            f'Búsqueda: "{nombre}"'
        )

    def _opcion_id(self) -> None:

        try:

            id_equipo = int(
                input(
                    "Ingresá el ID del equipo: "
                )
            )

        except ValueError:

            print(
                "⚠️ Ese no es un número válido.\n"
            )

            return

        resultados = self._servicio.obtener_por_id(
            id_equipo
        )

        self._mostrar_resultados(
            resultados,
            f"Equipo con ID {id_equipo}"
        )

    def ejecutar(self) -> None:

        opciones = {
            "1": (
                "Buscar equipo por nombre",
                self._opcion_buscar
            ),

            "2": (
                "Buscar equipo por ID",
                self._opcion_id
            ),

            "3": (
                "Salir",
                None
            ),
        }

        while True:

            print(
                "\n=== ⚽ Explorador de Equipos de Fútbol ==="
            )

            for clave, (etiqueta, _) in opciones.items():

                print(
                    f"{clave}. {etiqueta}"
                )

            eleccion = input(
                "Elegí una opción: "
            ).strip()

            if eleccion == "3":

                print(
                    "⚽ ¡Hasta la próxima!"
                )

                break

            elif eleccion in opciones:

                _, accion = opciones[eleccion]

                accion()

            else:

                print(
                    "⚠️ Opción inválida, "
                    "intentá de nuevo.\n"
                )


def main() -> None:

    cliente = FootballClient()

    servicio = FootballService(
        cliente
    )

    reporte = ReporteHTML()

    menu = MenuInteractivo(
        servicio,
        reporte
    )

    menu.ejecutar()


if __name__ == "__main__":
    main()
