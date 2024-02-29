import asyncio
import websockets
import json
from datetime import datetime
from getmac import get_mac_address

#Read the IP and PORT from environment
IP = '0.0.0.0'
PORT = '5000'
MID_FILE_PATH = './mid.json'

def get_props():
    return [ {
            "table_name": "cpu_info",
            "attribute": [
                "cpu_device_id",
                "model",
                "manufacturer",
                "processor_type",
                "cpu_status",
                "number_of_cores",
                "logical_processors",
                "address_width",
                "current_clock_speed",
                "max_clock_speed",
                "socket_designation",
                "availability",
                "number_of_efficiency_cores",
                "number_of_performance_cores",
                "created_at"
            ],
            "interval": 60,
            "code": "cpuInfo",
        },]

def get_mac_from_ip(ip):
    status = False
    mac = None
    try:
        mac = get_mac_address(ip=ip)
        if mac is not None:
            mac = mac.replace(':','') if mac else mac  
            status = True
            print("Success :-> ",f"Mac address of this '{ip}' is {mac}")
        else:
            print("Info :-> ",f"Unable to find the mac address of this '{ip}' ip.")
    except Exception as e:
        print("Error :-> ",f"Unable to find the mac address of this '{ip}' ip.",e)
    finally:
        return {
            "status":status,
            "mac":mac
        }
    
def get_host(mac):
    data = {}
    with open(MID_FILE_PATH, 'r') as file:
        data = json.load(file)
    return {
        'status':True,
        'data':{
            'mac':data[mac],
            'machine_id':mac
        }
    }  if mac in list(data.keys()) else {
        'status':False,
        'data':None
    }
 
def update_machine_id(machine_id,mac_address):
    data = {}
    with open(MID_FILE_PATH, 'r') as file:
        data = json.load(file)
    data[mac_address] = machine_id
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=4)

#Clients in hash table
ACTIVE_CLIENTS = {}

#Function to connect the clients
async def connect_client(websocket):
    status = False
    ip = None
    try:
        client_ip, _ = websocket.remote_address
        ip = client_ip
        ACTIVE_CLIENTS[client_ip] = {
            'machine_id':None,
            'socket':websocket
        }
        status = True
        print("Success :-> ",f"Client {client_ip} is connected.")
    except Exception as e:
        print("Error :-> ","There is an error to connect the client.")
    finally:
        return {
            "status":status,
            "ip":ip
        }

#Function to disconnect the client 
async def disconnect_client(ip):
    status = False
    try:
        if ip in ACTIVE_CLIENTS:
            await ACTIVE_CLIENTS[ip].get('socket').close()
            del ACTIVE_CLIENTS[ip]
        status = True
        print("Success :-> ",f"Client {ip} is disconnected.")
    except Exception as e:
        print('Error :-> ',"There is an error to disconnect the client or client is exists.",e)
    finally:
        return status
    
#Function to verify 
async def verify_client(ip):
    status = False
    client = None
    try:
        mac = None
        if ip != IP:
            mac = get_mac_from_ip(ip)
        else:
            try:
                mac = get_mac_address()
                mac = mac.replace(':','') if mac else mac
                mac = {
                    'status':True,
                    'mac':mac
                }
            except Exception as e:
                mac = {
                    'status':False,
                    'mac':None
                }
        if mac.get('status'):
            mac_mid = get_host(mac['mac'])
            if mac_mid['status']:
                client = mac_mid['data']
                status = True
                print("Success :-> ",f"Client {ip} is verified")
            else:
                print("Info :-> ",f"Unable to find the {ip} client.")
        else:
            print("Info :-> ",f"Unable to extract mac of this client {ip}.")
    except Exception as e:
        print("Error :-> ","There is an error to verify the client.",e)
    finally:
        return {
            'status':status,
            'client':client
        }

#Function to handle the client or its events
async def handle_client(websocket):
    client_connected = await connect_client(websocket)
    client = client_connected.get('ip')
    if client in ACTIVE_CLIENTS:
        async for message in websocket:
            event = None
            data = None
            try:
                message = json.loads(message)
                event = message.get('event')
                data = message.get('data')
            except Exception as e:
                print("Error :-> ",f"Communication format is not valid for the client {client}.")
                await disconnect_client(client)
            match event:
                case 'register':
                    props = get_props()
                    res = {
                            "status":True,
                            "message":'Properties are fetched.',
                            "properties":props
                        }
                    res = json.dumps(res)
                    await websocket.send(f"{res}")
                    await disconnect_client(client)
                case 'send_properties':
                    message = ''
                    status = False
                    print(
                            data.get('code'),
                            data.get('attributes')
                        )
                    res = {
                            "status":True,
                            "message":'Attribute get.',
                        }
                    res = json.dumps(res)
                    await websocket.send(f"{res}")
                case 'disconnect':
                    await disconnect_client(client)
    else:   
        print("Info :-> ","Can't find the client in the active session.")
        await disconnect_client(client)

#Function to start the server 
async def start_server(ip, port):
    server = await websockets.serve(handle_client, ip, port,ping_timeout=None)
    print("Success :-> ",f"Server is listening on ws://{ip}:{port}")
    await server.wait_closed() 

#Function to stop the server
async def stop_server():
    #Gather all async taska and cancel one by one
    tasks = [t for t in asyncio.all_tasks() if t != asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

#Function to run the server
async def run_server(ip,port):
    await start_server(ip,port)


try:
    asyncio.run(
        run_server(
            IP,
            PORT
        )
    )
except KeyboardInterrupt:
    asyncio.run(
        stop_server()
    )
    print("Info :-> ","Server is stopped.")
except Exception as e:
    print("Info :-> ","There is an error to start the server.",e)
