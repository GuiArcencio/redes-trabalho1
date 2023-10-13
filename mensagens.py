import re

from grader.tcp import Conexao
from estado_irc import EstadoIRC

def validar_nome(nome: bytes) -> bool:
    return re.match(br'^[a-zA-Z][a-zA-Z0-9_-]*$', nome) is not None

def interpretar_mensagem(conexao: Conexao, msg: bytes):
    campos = msg.strip(b' \r\n').split(b' ')
    if len(campos) < 2: return

    verbo = campos[0].upper()
    if verbo == b'PING':
        tratar_ping(conexao, b' '.join(campos[1:]))
    elif verbo == b'NICK':
        tratar_nick(conexao, b' '.join(campos[1:]))

def tratar_ping(conexao: Conexao, payload: bytes):
    conexao.enviar(b':server PONG server :%s\r\n' % payload)

def tratar_nick(conexao: Conexao, apelido: bytes):
    if not validar_nome(apelido):
        conexao.enviar(b':server 432 %s %s :Erroneous nickname\r\n' % (conexao._apelido, apelido))
        return
    
    estado = EstadoIRC.obter()
    disponivel = estado.tentar_apelido_novo(conexao._apelido, apelido, conexao)
    EstadoIRC.liberar()

    if disponivel:
        if conexao._apelido == b'*':
            conexao.enviar(b':server 001 %s :Welcome\r\n' % apelido)
            conexao.enviar(b':server 422 %s :MOTD File is missing\r\n' % apelido)
        else:
            conexao.enviar(b':%s NICK %s\r\n' % (conexao._apelido, apelido))

        conexao._apelido = apelido 
    else:
        conexao.enviar(b':server 433 %s %s :Nickname is already in use\r\n' % (conexao._apelido, apelido))