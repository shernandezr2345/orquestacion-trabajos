import os
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

VERIFICACION = """
import sys
from pathlib import Path
import orquestacion_trabajos
from orquestacion_trabajos.api.app import create_app
from orquestacion_trabajos.config.procesamiento import procesar_eventos
from orquestacion_trabajos.config.bootstrap import componer_componentes
from orquestacion_trabajos.modulos.trabajos.infraestructura.esquemas.v1.orquestacion import SolicitarCotizacionV1
package = Path(orquestacion_trabajos.__file__).resolve()
assert package.is_relative_to(Path(sys.prefix).resolve())
assert not package.is_relative_to(Path(sys.argv[1]).resolve())
assert create_app().title == "Orquestación de Trabajos"
assert callable(procesar_eventos)
assert callable(componer_componentes)
assert SolicitarCotizacionV1.schema()["name"] == "SolicitarCotizacionV1"
print(f"Wheel verificado fuera del repositorio: {package}")
"""


def main() -> None:
    proyecto = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="orquestacion-distribution-") as directorio_temporal:
        temporal = Path(directorio_temporal)
        ruta_entorno = temporal / "environment"
        entorno = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(ruta_entorno)}
        subprocess.run(
            ["uv", "sync", "--locked", "--no-editable", "--no-dev"],
            cwd=proyecto,
            env=entorno,
            check=True,
        )
        subprocess.run(
            ["uv", "build", "--out-dir", str(temporal / "dist")],
            cwd=proyecto,
            check=True,
        )
        source_archive = next((temporal / "dist").glob("*.tar.gz"))
        with tarfile.open(source_archive) as archive:
            names = {
                str(Path(name).relative_to(Path(name).parts[0])) for name in archive.getnames()
            }
        required = {"alembic.ini", "migraciones/env.py", "migraciones/script.py.mako"}
        required.update(
            str(path.relative_to(proyecto))
            for path in (proyecto / "migraciones/versions").glob("*.py")
        )
        if missing := required - names:
            raise RuntimeError(f"La distribución fuente omite migraciones: {sorted(missing)}")
        wheel = next((temporal / "dist").glob("*.whl"))
        interprete = ruta_entorno / "bin" / "python"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(interprete),
                "--no-deps",
                "--reinstall",
                str(wheel),
            ],
            check=True,
        )
        subprocess.run(
            [str(interprete), "-I", "-c", VERIFICACION, str(proyecto / "src")],
            cwd=temporal,
            check=True,
        )


if __name__ == "__main__":
    main()
