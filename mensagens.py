from grader.tcp import Conexao

def interpretar_mensagem(conexao: Conexao, msg: str):
    campos = msg.strip(' \r\n').split(' ')
    if len(campos) < 2: return

    if campos[0] == 'PING':
        tratar_ping(conexao, ' '.join(campos[1:]))

def tratar_ping(conexao: Conexao, payload: str):
    conexao.enviar(f':server PONG server :{payload}\r\n'.encode('utf-8'))