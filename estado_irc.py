from asyncio import Lock

# Singleton de dados do servidor
class EstadoIRC:
    _instancia = None
    _mutex = Lock()

    @classmethod
    async def obter(cls):
        await cls._mutex.acquire()

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