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
        self._conexoes: dict[bytes, Conexao] = dict()
        self._canais: dict[bytes, set[Conexao]] = dict()

    def tentar_apelido_novo(self, apelido_atual: bytes, apelido: bytes, conexao: Conexao) -> bool:
        if apelido.lower() in self._conexoes.keys():
            return False
        
        if apelido_atual != b'*':
            self._conexoes.pop(apelido_atual.lower())

        self._conexoes[apelido.lower()] = conexao
        return True

    def procurar_destinatario(self, destinatario: bytes) -> Conexao | None:
        return self._conexoes.get(destinatario.lower(), None)
    
    def procurar_canal(self, canal: bytes) -> set[Conexao] | None:
        return self._canais.get(canal.lower(), None)
    
    def adicionar_membro_ao_canal(self, conexao: Conexao, canal: bytes) -> set[Conexao]:
        canal = canal.lower()

        if canal not in self._canais.keys():
            self._canais[canal] = set()

        self._canais[canal].add(conexao)
        return self._canais[canal]
