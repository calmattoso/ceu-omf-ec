# coding: utf-8

import os
import re
import uuid
import json
import pika
import time

# -------------------------------------------------------------------------------
# Configuração

server = 'localhost'
port = 5672
vhost = '/'
username = 'guest'
passwd = 'guest'

myid = 'omf-rc'
mypid = os.getpid()
myaddr = 'amqp://{0}/frcp.{1}'.format(server, myid)

# ------------------------------------------------------------------------------
# Variáveis globais

uid            = None
hrn            = None
binary         = None
topic_app      = None
topic_app_addr = None
topic_exp      = None
resource_addr  = None
date_LA        = None
ping_google    = None

topics_subscribed = []
topics_created    = []

# -------------------------------------------------------------------------------
# Conexão AMQP

credentials = pika.PlainCredentials(username, passwd)
parameters = pika.ConnectionParameters(server, port, vhost, credentials)
connection = pika.BlockingConnection(parameters)

channel = connection.channel()

# -------------------------------------------------------------------------------
# Gerência dos tópicos.

def create_topic(name):
    channel.exchange_declare(exchange=name, type='topic', durable=False, auto_delete=True)
    r = channel.queue_declare(exclusive=True, auto_delete=True, durable=False)
    q = r.method.queue
    channel.queue_bind(exchange=name, queue=q, routing_key='o.*')
    topics_created.append({ 'exchange' : name, 'queue' : q, 'key' : 'o.*' })
    return q

def subscribe_topic(name):
    r = channel.queue_declare(exclusive=True, auto_delete=True, durable=False)
    q = r.method.queue
    channel.queue_bind(exchange=name, queue=q, routing_key='o.*')
    topics_subscribed.append({ 'exchange' : name, 'queue' : q, 'key' : 'o.*' })
    return q

def finalize_topics():
    global topics_subscribed
    global topics_created

    # Unsubscribe
    tmp = topics_subscribed
    topics_subscribed = []

    for t in tmp:
        channel.queue_unbind(exchange=t['exchange'], queue=t['queue'], routing_key=t['key'])
        channel.queue_delete(queue=t['queue'])

    # Apaga os tópicos criados pelo RC.
    # Mas mantém o próprio tópico do RC.
    tmp = topics_created
    topics_created = []

    for t in tmp:
        if t['exchange'] != myid:
            channel.queue_unbind(exchange=t['exchange'], queue=t['queue'], routing_key=t['key'])
            channel.queue_delete(queue=t['queue'])
            channel.exchange_delete(exchange=t['exchange'])
        else:
            topics_created.append(t)

# -------------------------------------------------------------------------------
# Criar as callbacks para tratar as mensagens

def omfrc_app_cb(ch, method, properties, body):
    msg = json.loads(body)

    # Ignorar mensagens enviadas por mim mesmo.
    if msg['src'] == myaddr or msg['src'] == resource_addr:
        # print "[INFO] Ignoring message"
        return

    print "------------------------------------------------------------"
    print "[INFO] _Application callback"
    print "[%s] %r:%r" % (myid, method.routing_key, body)
    
    global ping_google
    global date_LA

    # Parte 3: Executando a aplicação criada.
    if msg['op'] == 'configure' and 'guard' in msg and 'type' in msg['guard'] :

        # Make sure to only handle each app once...
        if msg['guard']['name'] == 'ping_google':
            if ping_google:
                return
            else:
                ping_google = True
        elif msg['guard']['name'] == 'date_LA':
            if date_LA:
                return
            else:
                date_LA = True

        print
    
        # Publicando a resposta da inicialização.
        resp = {
            'src'     : resource_addr,
            'cid'     : msg['mid'],
            'mid'     : str(uuid.uuid4()),
            'op'      : 'inform',
            'ts'      : msg['ts'],
            'replyto' : uid,
            'itype'   : 'STATUS',
            'props'   : {
                'type'    : 'application',
                'state'   : 'created',
                'hrn'     : msg['guard']['name']
            }
        }

	#Publicando no tópico "???_application".
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_app,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # Publicando no tópico do recurso criado.
        channel.basic_publish(exchange=uid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # ------------------------------------------------------------
        # Parte 4: Thread para criar e acompanhar a aplicação.
        # XXX: Como não temos aplicação ainda, vamos apenas simular as mensagens

        # TODO: iniciar a aplicação.

        resp = {
            'src'     : resource_addr,
            'itype'   : 'STATUS',
            'op'      : 'inform',
            'mid'     : str(uuid.uuid4()),
            'ts'      : msg['ts'],
            'replyto' : uid,
            'props'   : {
                'type'    : 'application',
                'status_type' : 'APP_EVENT',
                'event'       : 'STARTED',
                'app'         : msg['guard']['name'],
                'msg'         : msg['guard']['name'] + ' started',
                'seq'         : 1,
                'uid'         : uid,
                'hrn'         : msg['guard']['name']
            }
        }
            
        # Publicando no tópico "???_application".
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_app,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # Publicando no tópico do recurso criado.
        channel.basic_publish(exchange=uid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # ------------------------------------------------------------
        # Parte 5: Enviar saída do programa para o EC.
        # XXX: vamos simular que a aplicação enviou dados de saída.

        time.sleep(1)

        resp = {
            'src'   : resource_addr,
            'itype' : 'STATUS',
            'op'    : 'inform',
            'mid'   : str(uuid.uuid4()),
            'ts'    : msg['ts'],
            'props' : {
                'status_type' : 'APP_EVENT',
                'event'       : 'STDOUT',
                'type'        : 'application',
                'app'         : msg['guard']['name'],
                'msg'         : msg['guard']['name'] + ' produced a result',
                'seq'         : 2,
                'uid'         : uid,
                'hrn'         : msg['guard']['name']
            }
        }

        # Publicando no tópico "???_application".
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_app,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # Publicando no tópico do recurso criado.
        channel.basic_publish(exchange=uid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 
        

        # ------------------------------------------------------------
        # Parte 6: Avisar o término da aplicação.
        # XXX: vamos simular o término da aplicação.

        time.sleep(1)

        resp = {
            'src'   : resource_addr,
            'itype' : 'STATUS',
            'op'    : 'inform',
            'mid'   : str(uuid.uuid4()),
            'ts'    : msg['ts'],
            'props' : {
                'status_type' : 'APP_EVENT',
                'event'       : 'EXIT',
                'type'        : 'application',
                'app'         : msg['guard']['name'],
                'exit_code'   : 0,
                'msg'         : 0,
                'state'       : 'stopped',
                'seq'         : 3,
                'uid'         : uid,
                'hrn'         : msg['guard']['name']
            }
        }

        # Publicando no tópico "???_application".
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_app,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # Publicando no tópico do recurso criado.
        channel.basic_publish(exchange=uid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

def omfrc_resource_cb(ch, method, properties, body):
    msg = json.loads(body)

    # Ignorar mensagens enviadas por mim mesmo.
    if msg['src'] == myaddr or msg['src'] == resource_addr:
        # print "[INFO] Ignoring message"
        return

    print "------------------------------------------------------------"
    print "[INFO] Resource callback"
    print "[%s] %r:%r" % (myid, method.routing_key, body)


def omfrc_experiment_cb(ch, method, properties, body):
    msg = json.loads(body)

    # Ignorar mensagens enviadas por mim mesmo.
    if msg['src'] == myaddr:
    #    print "[INFO] Ignoring message"
        return

    print "------------------------------------------------------------"
    print "[INFO] Experiment callback"
    print "[%s] %r:%r" % (myid, method.routing_key, body)

    global uid
    global hrn
    global binary
    global topic_app
    global topic_app_addr
    global topic_exp
    global resource_addr
    
    # Parte 2: Criando uma aplicação
    if msg['op'] == 'create' and 'props' in msg and 'membership' in msg['props']:
        
        patt = 'amqp://[^/]+/frcp.(.+)'
        m = re.search(patt, msg['src'])
        src = m.group(1)

        m = re.search(patt, msg['props']['membership'])
        topic = m.group(1)

        topic_app = topic        
        topic_app_addr = 'amqp://{0}/frcp.{1}'.format(server, topic_app)
        binary = msg['props']['binary_path']
       
        # Gerar um novo UUID para o novo recurso. Recurso filho pedido pelo EC.
        uid = str(uuid.uuid4())        
        hrn = msg['props']['hrn']
        
        # Criar um novo tópico para o novo recurso.
        q = create_topic(uid)
        channel.basic_consume(omfrc_resource_cb, queue=q)
        
        # Inscrevendo-se no canal '***_application'
        q = subscribe_topic(topic)
        channel.basic_consume(omfrc_app_cb, queue=q)
        
        # Endereço do recurso
        resource_addr = 'amqp://{0}/frcp.{1}'.format(server, uid)   
       
        # Publicando resposta de criação.
        resp = {
            'src'     : myaddr,
            'cid'     : msg['mid'],
            'op'      : 'inform',
            'mid'     : str(uuid.uuid4()),
            'ts'      : msg['ts'],
            'replyto' : myid,
            'itype'   : 'CREATION.OK',
            'props'   : {
                'uid'         : uid,
                'res_id'      : str(uuid.uuid4()),
                'binary_path' : msg['props']['binary_path'],
                'hrn'         : msg['props']['hrn'],
                'membership'  : [msg['props']['membership']],
                'type'        : 'application',
                'address'     : resource_addr
            }
        }

	#Publicando no tópico do experimento
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_exp,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

	#Publicando no RC
        channel.basic_publish(exchange=myid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        resp = {
            'src'     : resource_addr,
            'type'    : 'application',
            'op'      : 'inform',
            'mid'     : str(uuid.uuid4()),
            'ts'      : msg['ts'],
            'itype'   : 'STATUS',
            'props'   : {
                'hrn'         : msg['props']['hrn'],
                'membership'  : [msg['props']['membership']]
            }
        }

        #Publicando no tópico "???_application"
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_app,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json'))    

    # ------------------------------------------------------------
    # Parte 7: Terminar o experimento.

    if msg['op'] == 'configure' and 'props' in msg and 'membership' in msg['props'] and 'leave' in msg['props']['membership'] :
        
        resp = {
            'src'     : myaddr,
            'cid'     : msg['mid'],
            'op'      : 'inform',
            'mid'     : str(uuid.uuid4()),
            'ts'      : msg['ts'],
            'replyto' : myid,
            'itype'   : 'STATUS',
            'props'   : {
                'membership' : []
            }
        }

	#Publicando no RC
        resp = json.dumps(resp)
        channel.basic_publish(exchange=myid,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json')) 

        # Reinicializa as variáveis globais.
        uid            = None
        hrn            = None
        binary         = None
        topic_app      = None
        topic_app_addr = None
        topic_exp      = None
        resource_addr  = None

        # Unsubscribe e remoção dos tópicos.
        finalize_topics()

        
def omfrc_cb(ch, method, properties, body):
    msg = json.loads(body)

    # Ignorar mensagens enviadas por mim mesmo.
    if msg['src'] == myaddr:
        #print "[INFO] Ignoring message"
        return
    
    print "------------------------------------------------------------"
    print "[INFO] RC callback"
    print "[%s] %r:%r" % (myid, method.routing_key, body)

    # Parte 1: Entrando em um experimento.
    if msg['op'] == 'configure' and 'props' in msg and 'res_index' in msg['props']:
 
        patt = 'amqp://[^/]+/frcp.(.+)'
        m = re.search(patt, msg['src'])
        src = m.group(1)

        m = re.search(patt, msg['props']['membership'])
        topic = m.group(1)

        # Guarda o tópico do experimento
        global topic_exp
        topic_exp = topic

        global date_LA
        global ping_google

        date_LA = False
        ping_google = False

	#Inscrevendo no tópido do experimento
        q = subscribe_topic(topic)
        channel.basic_consume(omfrc_experiment_cb, queue=q)

        resp = {
            'src'     : myaddr,
            'cid'     : msg['mid'],
            'op'      : 'inform',
            'mid'     : str(uuid.uuid4()),
            'ts'      : msg['ts'],
            'rp' : myid,
            'itype'   : 'STATUS',
            'props'   : {
                'membership' : [msg['props']['membership']],
                'res_index'  : msg['props']['res_index'],
                'address'     : myaddr
            }
        }

	# Publicando no tópido do experimento.
        resp = json.dumps(resp)
        channel.basic_publish(exchange=topic_exp,
                              routing_key='o.info',
                              body=resp,
                              properties=pika.BasicProperties(content_type='text/json'))

       

        
def omfrc_pid_cb(ch, method, properties, body):
    omfrc_cb(ch, method, properties, body)

# -------------------------------------------------------------------------------
# Cria os tópicos e associa as callbacks
#
queue1 = create_topic(myid)
queue2 = create_topic('{0}-{1}'.format(myid, mypid))

channel.basic_consume(omfrc_cb, queue=queue1, no_ack=True)
channel.basic_consume(omfrc_pid_cb, queue=queue2, no_ack=True)


# -------------------------------------------------------------------------------
# Espera pelas mensagens
#
print 'RC running... to exit press CTRL+C'
channel.start_consuming()
