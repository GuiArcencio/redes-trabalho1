from __future__ import annotations
from threading import Lock
from grader.tcp import Conexao

# Singleton de dados do servidor
class EstadoIRC:
    _instancia = None
    _mutex = Lock()

    @classmethod
    def obter(cls) -> EstadoIRC:
        cls._mutex.acquire()

        if cls._instancia is None:
            cls._instancia = EstadoIRC()
        
        return cls._instancia
    
    @classmethod
    def liberar(cls):
        cls._mutex.release()
    
    def __init__(self):
        self._apelidos_usados = set()
        self._conexoes = dict()
        self._canais = dict()

    def tentar_apelido_novo(self, apelido_atual: bytes, apelido: bytes, conexao: Conexao) -> bool:
        if apelido.lower() in self._apelidos_usados:
            return False
        
        if apelido_atual != b'*':
            self._apelidos_usados.remove(apelido_atual.lower())
            self._conexoes.pop(apelido_atual)

        self._apelidos_usados.add(apelido.lower())
        self._conexoes[apelido] = conexao
        return True

