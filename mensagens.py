import re
import asyncio

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
        tratar_nick(conexao, campos[1])
    elif verbo == b'PRIVMSG' and len(campos) >= 3:
        if campos[1][0:1] == b'#':
            tratar_privmsg_canal(conexao, campos[1], b' '.join(campos[2:]))
        else:
            tratar_privmsg_pessoal(conexao, campos[1], b' '.join(campos[2:]))
    elif verbo == b'JOIN' and conexao._apelido != b'*':
        tratar_join(conexao, campos[1])
    elif verbo == b'PART':
        tratar_part(conexao, campos[1])


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

def tratar_privmsg_pessoal(conexao: Conexao, destinatario: bytes, conteudo: bytes):
    if conexao._apelido != b'*' and len(conteudo) >= 2 and conteudo[0:1] == b':':
        estado = EstadoIRC.obter()
        conexao_destinatario = estado.procurar_destinatario(destinatario)
        EstadoIRC.liberar()

        if conexao_destinatario is not None:
            conexao_destinatario.enviar(b':%s PRIVMSG %s %s\r\n' % (conexao._apelido, conexao_destinatario._apelido, conteudo))

def tratar_privmsg_canal(conexao: Conexao, canal: bytes, conteudo: bytes):
    if conexao._apelido != b'*' and len(conteudo) >= 2 and conteudo[0:1] == b':':
        estado = EstadoIRC.obter()
        conexoes_canal = estado.procurar_canal(canal)
        EstadoIRC.liberar()

        if conexoes_canal is not None:
            mensagens = set()
            for membro in conexoes_canal:
                if membro is not conexao:
                    mensagem = asyncio.create_task(
                        enviar_assincrono(membro, b':%s PRIVMSG %s %s\r\n' % (conexao._apelido, canal.lower(), conteudo))
                    )
                    mensagens.add(mensagem)
                    mensagem.add_done_callback(mensagens.discard)

def tratar_join(conexao: Conexao, canal: bytes):
    if canal[0:1] == b'#' and validar_nome(canal[1:]):
        estado = EstadoIRC.obter()
        membros = estado.adicionar_membro_ao_canal(conexao, canal)
        EstadoIRC.liberar()
        conexao._canais.add(canal.lower())

        mensagens = set()
        for membro in membros:
            if membro is not conexao:
                mensagem = asyncio.create_task(
                    enviar_assincrono(membro, b':%s JOIN :%s\r\n' % (conexao._apelido, canal.lower()))
                )
                mensagens.add(mensagem)
                mensagem.add_done_callback(mensagens.discard)
        conexao.enviar(b':%s JOIN :%s\r\n' % (conexao._apelido, canal.lower()))

        nomes_membros = sorted(list(map((lambda c: c._apelido.lower()), membros)))
        msg_buffer = b':server 353 %s = %s :' % (conexao._apelido, canal.lower())
        for nome in nomes_membros:
            if len(msg_buffer + nome) < 510:
                msg_buffer = msg_buffer + nome + b' '
            else:
                msg_buffer = msg_buffer[:-1] + b'\r\n'
                conexao.enviar(msg_buffer)
                msg_buffer = b':server 353 %s = %s :%s ' % (conexao._apelido, canal.lower(), nome)
        msg_buffer = msg_buffer[:-1] + b'\r\n'
        conexao.enviar(msg_buffer)
        conexao.enviar(b':server 366 %s %s :End of /NAMES list.\r\n' % (conexao._apelido, canal.lower()))
    else:
        conexao.enviar(b':server 403 %s :No such channel\r\n' % canal)

def tratar_part(conexao: Conexao, canal: bytes):
    canal = canal.lower()
    if canal in conexao._canais:
        estado = EstadoIRC.obter()
        membros = estado.remover_membro_de_canal(conexao, canal)
        EstadoIRC.liberar()
        conexao._canais.remove(canal)

        mensagens = set()
        for membro in membros:
            mensagem = asyncio.create_task(
                enviar_assincrono(membro, b':%s PART %s\r\n' % (conexao._apelido, canal.lower()))
            )
            mensagens.add(mensagem)
            mensagem.add_done_callback(mensagens.discard)

        conexao.enviar(b':%s PART %s\r\n' % (conexao._apelido, canal.lower()))

def tratar_saida(conexao: Conexao):
    estado = EstadoIRC.obter()
    colegas = estado.remover_de_todos_canais(conexao)
    EstadoIRC.liberar()

    mensagens = set()
    for colega in colegas:
        mensagem = asyncio.create_task(
            enviar_assincrono(colega, b':%s QUIT :Connection closed\r\n' % conexao._apelido)
        )
        mensagens.add(mensagem)
        mensagem.add_done_callback(mensagens.discard)

async def enviar_assincrono(conexao: Conexao, dados: bytes):
    return conexao.enviar(dados)