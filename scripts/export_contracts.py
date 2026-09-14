import argparse
import importlib.util
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    infrastructure = root / "src/orquestacion_trabajos/infraestructura"
    contracts = [
        ("entrada", "SolicitudListaV1", "solicitud_de_partner_lista_v1", "solicitud-lista"),
        ("orquestacion", "TrabajoCreadoV1", "trabajo_creado_v1", "trabajo-creado"),
        (
            "orquestacion",
            "SolicitarCotizacionV1",
            "solicitar_cotizacion_v1",
            "solicitar-cotizacion",
        ),
        (
            "cotizaciones",
            "CotizacionRegistradaV1",
            "cotizacion_registrada_v1",
            "cotizacion-registrada",
        ),
        (
            "cotizaciones",
            "CotizacionRechazadaV1",
            "cotizacion_rechazada_v1",
            "cotizacion-rechazada",
        ),
    ]
    different = []
    for module_name, class_name, internal_name, public_name in contracts:
        path = infrastructure / "esquemas_python/v1" / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        schema = getattr(module, class_name).schema()
        for destination in (
            infrastructure / "esquemas" / f"{internal_name}.avsc",
            root / "docs/contratos" / f"{public_name}-v1.avsc",
        ):
            if arguments.check:
                if not destination.exists() or json.loads(destination.read_text()) != schema:
                    different.append(str(destination))
            elif not destination.exists() or json.loads(destination.read_text()) != schema:
                destination.write_text(json.dumps(schema, indent=2) + "\n")
    if different:
        print("\n".join(different))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
