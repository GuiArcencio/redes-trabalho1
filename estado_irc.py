# Singleton de dados do servidor
class EstadoIRC:
    _instancia = None

    @classmethod
    def obter(cls):
        if cls._instancia is None:
            cls._instancia = EstadoIRC()
        
        return cls._instancia
    
    def __init__(self):
        self._apelidos_usados = set()
        self._conexoes = dict()
        self._canais = dict()