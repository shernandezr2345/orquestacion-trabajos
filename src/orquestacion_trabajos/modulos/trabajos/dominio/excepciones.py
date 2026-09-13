from __future__ import annotations


class DominioError(Exception):
    pass


class CotizacionAjenaError(DominioError):
    pass


class ResultadoIncompatibleError(DominioError):
    pass


class VersionEsperadaIncompatibleError(DominioError):
    pass


class EstadoTrabajoInvalidoError(DominioError):
    pass
