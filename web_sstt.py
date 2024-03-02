# coding=utf-8
#!/usr/bin/env python3

import socket
import selectors    #https://docs.python.org/3/library/selectors.html
import select
import types        # Para definir el tipo de datos data
import argparse     # Leer parametros de ejecución
import os           # Obtener ruta y extension
# import multiprocessing
from datetime import datetime, timedelta # Fechas de los mensajes HTTP
import time         # Timeout conexión
import sys          # sys.exit
import re           # Analizador sintáctico
import logging      # Para imprimir logs


BUFSIZE = 8192 # Tamaño máximo del buffer que se puede utilizar
TIMEOUT_CONNECTION = 9+7+5+2+10 # Timout para la conexión persistente
MAX_ACCESOS = 10

# Extensiones admitidas (extension, name in HTTP)
filetypes = {"gif":"image/gif", "jpg":"image/jpg", "jpeg":"image/jpeg", "png":"image/png", "htm":"text/htm", 
             "html":"text/html", "css":"text/css", "js":"text/js"}

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)-7s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()


def enviar_mensaje(cs, data):
    """ Esta función envía datos (data) a través del socket cs
        Devuelve el número de bytes enviados.
    """
    bytes = cs.send(data)
    return bytes

def recibir_mensaje(cs):
    """ Esta función recibe datos a través del socket cs
        Leemos la información que nos llega. recv() devuelve un string con los datos.
    """
    buff_size = BUFSIZE
    data = cs.recv(buff_size)
    datos = data.decode()
    return datos


def cerrar_conexion(cs):
    """ Esta función cierra una conexión activa.
    """
    print("Cerrando conexión " + str(cs))
    cs.close()
    pass


def process_cookies(headers,  cs):
    """ Esta función procesa la cookie cookie_counter
        1. Se analizan las cabeceras en headers para buscar la cabecera Cookie
        2. Una vez encontrada una cabecera Cookie se comprueba si el valor es cookie_counter
        3. Si no se encuentra cookie_counter , se devuelve 1
        4. Si se encuentra y tiene el valor MAX_ACCESSOS se devuelve MAX_ACCESOS
        5. Si se encuentra y tiene un valor 1 <= x < MAX_ACCESOS se incrementa en 1 y se devuelve el valor
    """
    # for param in headers:
    #     if param[0] == 'Cookie':
    #         if re.fullmatch('cookie_counter=', param[1]):
    #             string = param[1].split('cookie_counter=')
    #             cookie_counter = re.match('^[0-9]+', string[1]).group()
    #             if cookie_counter == MAX_ACCESOS:
    #                 return MAX_ACCESOS
    #             elif cookie_counter >= 1 and cookie_counter < MAX_ACCESOS:
    #                 cookie_counter += 1
    #                 return cookie_counter
    #     else:
    #     return 1
    
    pass
            
def construir_cabeceras(tam, extension, cookie_counter, codigo):
    f = ''
    if codigo == 405:
        f += 'HTTP/1.1 405 Method Not Allowed\r\n'
        f += 'Allow: GET, POST\r\n'
    elif codigo == 404:
        f += 'HTTP/1.1 404 Not Found\r\n'
    elif codigo == 403:
        f += 'HTTP/1.1 403 Forbidden\r\n'
    else:
        f += 'HTTP/1.1 200 OK\r\n'
        f += 'Date: ' + datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT\r\n')
        f += 'Server: Servidor Python/1.0.0 (Linux)\r\n'
        f += 'Connection: Keep-Alive\r\n'
        f += 'Set-Cookie: ' + str(cookie_counter) + '\r\n'
        f += 'Content-Length: ' + str(tam) + '\r\n'
        if extension == 'html':
            f += 'Content-Type: text/' + str(extension) + '; charset=ISO-8859-1\r\n'
        else:
            f += 'Content-Type: image/' + str(extension) + '\r\n'
        f += '\r\n'
    return f.encode()

def construir_mensaje(ruta):
    f = b''
    fichero = open(ruta, 'rb')
    while read_bytes := fichero.read(BUFSIZE):
        f += read_bytes
    return f
    
def process_web_request(cs, webroot):
    rlist = [cs]
    wlist = []
    xlist = []
    while True:
        rsublist, _, _ = select.select(rlist, wlist, xlist, TIMEOUT_CONNECTION)
        if rsublist == []:
            print('Salta por timeout')
            cerrar_conexion(cs)
            break
        datos = recibir_mensaje(cs)
        # print(datos)
        
        lineas = datos.splitlines()
        parametros = [lineas[0].split(' ', 1)]
        parametros += [linea.split(': ', 1) for linea in lineas if ': ' in linea]    
        parametros = dict((item[0], item[1]) for item in parametros)
        
        diccionario = dict()
        patron = r'([^:]*)|:\s(.*)$'
        for linea in lineas:
            if re.match(r'^GET|^POST', linea):
                print('PRIMERA LINEA')
            elif linea != '':
                er = re.compile(patron)
                coin = er.fullmatch(linea)
                print(coin)
                #diccionario[er.group(1)] = er.group(2)
                
        print(diccionario)
        
        if parametros[0][1].split(' ')[1] == 'HTTP/1.1':
            print('Versión 1.1 de HTTP')
        
        if parametros[0][0] == 'GET':
            print('Método GET ' + parametros[0][1].split(' ')[0])
        elif parametros[0][0] == 'POST':
            print('Método POST')
        else:
            print('Method Not Allowed 405')
            construir_cabeceras(0, '', 0, 405)
            cerrar_conexion(cs)
        
        print("Conexión: " + str(cs))
        
        if parametros[0][1].split(' ')[0] == '/' or parametros[0][1].split(' ')[0] == '/index.html':
            parametros[0][1] = '/index.html'
        ruta_absoluta = webroot + parametros[0][1].split(' ')[0]
        
        if os.path.isfile(ruta_absoluta):
            tam = os.stat(ruta_absoluta).st_size
            extension = os.path.basename(ruta_absoluta).split('.')[1]
            cookie_counter = process_cookies(parametros, cs)
            print("Cookie counter: " + str(cookie_counter))
            if cookie_counter == MAX_ACCESOS:
                construir_cabeceras(0, '', cookie_counter, 403)
                cerrar_conexion(cs)
            else:
                resp = construir_cabeceras(tam, extension, cookie_counter, 200)
                resp += construir_mensaje(ruta_absoluta)
                bytes = enviar_mensaje(cs, resp)
        else:
            construir_cabeceras(0, '', 0, 404)
            cerrar_conexion(cs)
            
        
        
        
        
    """ Procesamiento principal de los mensajes recibidos.
        Típicamente se seguirá un procedimiento similar al siguiente (aunque el alumno puede modificarlo si lo desea)

        * Bucle para esperar hasta que lleguen datos en la red a través del socket cs con select() ->

            * Se comprueba si hay que cerrar la conexión por exceder TIMEOUT_CONNECTION segundos ->
              sin recibir ningún mensaje o hay datos. Se utiliza select.select

            * Si no es por timeout y hay datos en el socket cs. ->
                * Leer los datos con recv. ->
                * Analizar que la línea de solicitud y comprobar está bien formateada según HTTP 1.1 ->
                    * Devuelve una lista con los atributos de las cabeceras. ->
                    * Comprobar si la versión de HTTP es 1.1 ->
                    * Comprobar si es un método GET o POST. Si no devolver un error Error 405 "Method Not Allowed". ->
                    * Leer URL y eliminar parámetros si los hubiera
                    * Comprobar si el recurso solicitado es /, En ese caso el recurso es index.html ->
                    * Construir la ruta absoluta del recurso (webroot + recurso solicitado) ->
                    * Comprobar que el recurso (fichero) existe, si no devolver Error 404 "Not found" ->
                    * Analizar las cabeceras. Imprimir cada cabecera y su valor. Si la cabecera es Cookie comprobar
                      el valor de cookie_counter para ver si ha llegado a MAX_ACCESOS. ->
                      Si se ha llegado a MAX_ACCESOS devolver un Error "403 Forbidden" ->
                    * Obtener el tamaño del recurso en bytes. ->
                    * Extraer extensión para obtener el tipo de archivo. Necesario para la cabecera Content-Type ->
                    * Preparar respuesta con código 200. Construir una respuesta que incluya: la línea de respuesta y
                      las cabeceras Date, Server, Connection, Set-Cookie (para la cookie cookie_counter),
                      Content-Length y Content-Type.
                    * Leer y enviar el contenido del fichero a retornar en el cuerpo de la respuesta.
                    * Se abre el fichero en modo lectura y modo binario
                        * Se lee el fichero en bloques de BUFSIZE bytes (8KB)
                        * Cuando ya no hay más información para leer, se corta el bucle

            * Si es por timeout, se cierra el socket tras el período de persistencia.
                * NOTA: Si hay algún error, enviar una respuesta de error con una pequeña página HTML que informe del error.
    """

def main():
    """ Función principal del servidor
    """

    try:

        # Argument parser para obtener la ip y puerto de los parámetros de ejecución del programa. IP por defecto 0.0.0.0
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--port", help="Puerto del servidor", type=int, required=True)
        parser.add_argument("-ip", "--host", help="Dirección IP del servidor o localhost", required=True)
        parser.add_argument("-wb", "--webroot", help="Directorio base desde donde se sirven los ficheros (p.ej. /home/user/mi_web)")
        parser.add_argument('--verbose', '-v', action='store_true', help='Incluir mensajes de depuración en la salida')
        args = parser.parse_args()


        if args.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info('Enabling server in address {} and port {}.'.format(args.host, args.port))

        logger.info("Serving files from {}".format(args.webroot))

        """ Funcionalidad a realizar
        * Crea un socket TCP (SOCK_STREAM) ->
        * Permite reusar la misma dirección previamente vinculada a otro proceso. Debe ir antes de sock.bind ->
        * Vinculamos el socket a una IP y puerto elegidos ->

        * Escucha conexiones entrantes ->

        * Bucle infinito para mantener el servidor activo indefinidamente ->
            - Aceptamos la conexión ->

            - Creamos un proceso hijo -> 

            - Si es el proceso hijo se cierra el socket del padre y procesar la petición con process_web_request() ->

            - Si es el proceso padre cerrar el socket que gestiona el hijo. ->
        """
        s1 = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)
        s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s1.bind((args.host, args.port))
        
        s1.listen()

        while True:
            s2, data = s1.accept()
            """
            proceso = multiprocessing.Process(target=process_web_request(cs=s2, webroot=args.webroot))
            proceso.start()
            proceso.join()
            """
            pid = os.fork()

            if pid == 0:
                process_web_request(cs=s2, webroot=args.webroot)
            else:
                s2.close()
    except KeyboardInterrupt:
        True

if __name__== "__main__":
    main()
