from collections.abc import Callable
from typing import Any

import pulsar


class PublicadorPulsar:
    def __init__(
        self, url: str, topico: str, schema: Any, convertir: Callable[[dict[str, object]], Any]
    ) -> None:
        self.url = url
        self.topico = topico
        self.schema = schema
        self.convertir = convertir
        self._cliente: Any = None
        self._productor: Any = None

    def abrir(self) -> None:
        if self._productor is not None:
            return
        self._cliente = pulsar.Client(
            self.url, operation_timeout_seconds=1, connection_timeout_ms=1000
        )
        try:
            self._productor = self._cliente.create_producer(
                self.topico, schema=self.schema, send_timeout_millis=3000
            )
        except Exception:
            self.cerrar()
            raise

    def publicar(self, payload: dict[str, object], clave: str, properties: dict[str, str]) -> None:
        record = self.convertir(payload)
        self.abrir()
        try:
            self._productor.send(record, partition_key=clave, properties=properties)
        except Exception:
            self.cerrar()
            raise

    def cerrar(self) -> None:
        cliente = self._cliente
        self._cliente = self._productor = None
        if cliente is not None:
            try:
                cliente.close()
            except pulsar.AlreadyClosed:
                pass
