import logging
import os
import json
import webbrowser
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote


logging.basicConfig(
    filename="app.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class FootballClient:
    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"

    class APIConnectionError(Exception):
        pass

    class RecursoNoEncontrado(Exception):
        pass

    def _pedir(self, endpoint):
        url = f"{self.BASE_URL}/{endpoint}"

        request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        try:
            with urlopen(request, timeout=8) as response:
                return json.loads(response.read())

        except HTTPError as error:
            if error.code == 404:
                raise self.RecursoNoEncontrado(
                    "No se encontraron resultados."
                ) from error

            logging.error("Error HTTP: %s", error)
            raise self.APIConnectionError(
                f"Error del servidor: {error.code}"
            ) from error

        except URLError as error:
            logging.error("Error de conexión: %s", error)
            raise self.APIConnectionError(
                "No fue posible conectarse a la API."
            ) from error

        except json.JSONDecodeError as error:
            logging.error("JSON inválido: %s", error)
            raise self.APIConnectionError(
                "La API devolvió datos inválidos."
            ) from error

    def buscar_nombre(self, nombre):
        return self._pedir(
            f"searchteams.php?t={quote(nombre)}"
        )

    def buscar_id(self, id_equipo):
        return self._pedir(
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
        escudo
    ):
        self.nombre = nombre
        self.pais = pais
        self.liga = liga
        self.estadio = estadio
        self.fundacion = fundacion
        self.escudo = escudo

    @classmethod
    def from_json(cls, datos):
        return cls(
            datos.get("strTeam", "Desconocido"),
            datos.get("strCountry", "Desconocido"),
            datos.get("strLeague", "Desconocida"),
            datos.get("strStadium", "Desconocido"),
            datos.get("intFormedYear", "Desconocido"),
            datos.get("strBadge", "")
        )

    def __str__(self):
        return (
            f"{self.nombre}\n"
            f"  País: {self.pais}\n"
            f"  Liga: {self.liga}\n"
            f"  Estadio: {self.estadio}\n"
            f"  Fundación: {self.fundacion}"
        )


class FootballService:
    def __init__(self, cliente):
        self.cliente = cliente

    def _convertir(self, datos):
        return [
            Team.from_json(equipo)
            for equipo in datos.get("teams", []) or []
        ]

    def buscar_nombre(self, nombre):
        assert nombre.strip(), "El nombre no puede estar vacío."

        try:
            datos = self.cliente.buscar_nombre(nombre.strip())
            return self._convertir(datos)

        except FootballClient.RecursoNoEncontrado:
            return []

        except FootballClient.APIConnectionError as error:
            print(f"⚠️ {error}")
            return []

    def buscar_id(self, id_equipo):
        assert id_equipo >= 1, "El ID debe ser mayor o igual a 1."

        try:
            datos = self.cliente.buscar_id(id_equipo)
            return self._convertir(datos)

        except FootballClient.RecursoNoEncontrado:
            return []

        except FootballClient.APIConnectionError as error:
            print(f"⚠️ {error}")
            return []


class ReporteHTML:
    ARCHIVO = "reporte_equipos_futbol.html"

    CSS = """
    body {
        font-family: Arial;
        background: #071a12;
        color: white;
        padding: 30px;
    }

    h1 {
        color: #55e878;
        text-align: center;
    }

    .fecha {
        text-align: center;
        color: #aaa;
    }

    .grid {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 20px;
    }

    .card {
        background: #10291e;
        border-radius: 12px;
        width: 260px;
        overflow: hidden;
        box-shadow: 0 4px 12px #000;
    }

    img {
        width: 100%;
        height: 220px;
        object-fit: contain;
        background: white;
    }

    .info {
        padding: 15px;
    }

    h2 {
        color: #55e878;
    }
    """

    def tarjeta(self, equipo):
        imagen = equipo.escudo or "https://via.placeholder.com/260x220"

        return f"""
        <div class="card">
            <img src="{imagen}" alt="Escudo de {equipo.nombre}">
            <div class="info">
                <h2>{equipo.nombre}</h2>
                <p><b>País:</b> {equipo.pais}</p>
                <p><b>Liga:</b> {equipo.liga}</p>
                <p><b>Estadio:</b> {equipo.estadio}</p>
                <p><b>Fundación:</b> {equipo.fundacion}</p>
            </div>
        </div>
        """

    def generar(self, equipos, titulo):
        if equipos:
            contenido = "".join(
                self.tarjeta(equipo)
                for equipo in equipos
            )
            cuerpo = f'<div class="grid">{contenido}</div>'
        else:
            cuerpo = "<h2 style='text-align:center'>No se encontraron equipos.</h2>"

        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>{titulo}</title>
            <style>{self.CSS}</style>
        </head>

        <body>
            <h1>{titulo}</h1>

            <p class="fecha">
                Generado el {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
            </p>

            {cuerpo}
        </body>
        </html>
        """

        with open(self.ARCHIVO, "w", encoding="utf-8") as archivo:
            archivo.write(html)

        ruta = os.path.abspath(self.ARCHIVO)
        webbrowser.open(f"file://{ruta}")


class Menu:
    def __init__(self, servicio, reporte):
        self.servicio = servicio
        self.reporte = reporte

    def mostrar(self, equipos, titulo):
        self.reporte.generar(equipos, titulo)
        print(
            f"✅ Se generó el reporte con "
            f"{len(equipos)} equipo(s).\n"
        )

    def buscar_nombre(self):
        nombre = input("Ingresá el nombre del equipo: ")

        if not nombre.strip():
            print("⚠️ El nombre no puede estar vacío.")
            return

        equipos = self.servicio.buscar_nombre(nombre)

        self.mostrar(
            equipos,
            f'Búsqueda: "{nombre}"'
        )

    def buscar_id(self):
        try:
            id_equipo = int(
                input("Ingresá el ID del equipo: ")
            )

            equipos = self.servicio.buscar_id(id_equipo)

            self.mostrar(
                equipos,
                f"Equipo con ID {id_equipo}"
            )

        except ValueError:
            print("⚠️ Debés ingresar un número.")

        except AssertionError as error:
            print(f"⚠️ {error}")

    def ejecutar(self):
        while True:
            print("""
=== ⚽ Explorador de Equipos ===

1. Buscar equipo por nombre
2. Buscar equipo por ID
3. Salir
""")

            opcion = input("Elegí una opción: ").strip()

            if opcion == "1":
                self.buscar_nombre()

            elif opcion == "2":
                self.buscar_id()

            elif opcion == "3":
                print("⚽ ¡Hasta la próxima!")
                break

            else:
                print("⚠️ Opción inválida.")


def main():
    cliente = FootballClient()
    servicio = FootballService(cliente)
    reporte = ReporteHTML()
    menu = Menu(servicio, reporte)

    menu.ejecutar()


if __name__ == "__main__":
    main()
