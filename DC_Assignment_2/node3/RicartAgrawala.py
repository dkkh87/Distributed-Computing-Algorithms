import sys
import time
import threading
import socket
import json
import pickle

##################################################################################################################################
# Variabel declarations                                                                                                         #
##################################################################################################################################
REPLY = 0
REQUEST = 1
WANTED = 0
HELD = 1
RELEASED = 2
done = 0

#Stores the information of the local process
localInfo =     { 
                    'procName':         None,
                    'procPID':          None,   
                    'procState':        None,   
                    'procTimestamp':    None,   
                    'procAddr':         None,   
                    'procRemotes':      None 
                }

defferedQueue = []  #Waiting to reply too
replyQueue    = []  #Awaiting replies from
msgThread = None

remoteAddresses = { } #Store the addresses of the other processes

MAXRECV = 4096 
DEBUG = True
listeningSocket = None

##################################################################################################################################
#Auxillary functions                                                                                                            #
##################################################################################################################################
def MutexInit(localAddr, procPID, procName, remoteAddr, remoteName, numRemotes):
    #if DEBUG: print 'Entering --> MutexInit\n'
    global localInfo
    #Initalize the local process info
    localInfo['procName']        = procName
    localInfo['procPID']         = procPID
    localInfo['procState']       = RELEASED
    localInfo['procAddr']        = localAddr
    localInfo['procRemotes']     = numRemotes
    localInfo['procTimestamp'] = 0    #Generate the timestamp for the message

    #splitting the remoteAddr and remoteName tuples into separate variables
    remoteAddr1, remoteAddr2 = remoteAddr
    remoteName1, remoteName2 = remoteName #Don't know if we need this
    #remoteAddr1 = remoteAddr
    #remoteName1 = remoteName #Don't know if we need this

    #Add the other two processes addresses to a dictionary for access later
    remoteAddresses[remoteName1] = remoteAddr1
    remoteAddresses[remoteName2] = remoteAddr2
    #Create thread that is supposed to fork the messageListener function to run in the background 
    msgThread = threading.Thread(target = MessageListener)
    msgThread.start()
    #if DEBUG: print 'Exiting --> MutexInit'


##################################################################################################################################
# Messaging Functions                                                                                                          #
##################################################################################################################################
def send_dict_over_socket(dictionary, sock, address):
    # Serialize the dictionary
    serialized_dict = pickle.dumps(dictionary)
    # Convert the length of the serialized data to a fixed-length string representation
    data_length = str(len(serialized_dict)).ljust(MAXRECV)
    # Send the length of the serialized data first
    sock.sendto(data_length.encode(), address)
    # Send the serialized data
    sock.sendto(serialized_dict, address)

def SendMessage(addr, message):
    #if DEBUG: print 'Entering --> SendMessage\n'
    #if DEBUG: print ('Sending message --> {0}').format(message['procInfo']['procName'])
    sendingSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #messageStr = str(message)
    #sendingSocket.sendto(messageStr.encode(), addr)
    send_dict_over_socket(message, sendingSocket, addr)
    sendingSocket.close()

    #if DEBUG: print 'Exiting --> SendMessage'
    return True

def receive_dict_from_socket(sock):
    # Receive the fixed length string representation of the serialized data
    data_length_str = sock.recv(MAXRECV).decode().strip()
    # Receive the serialized data
    serialized_data = sock.recv(int(data_length_str))
    # Deserialize the data into a dictionary
    dictionary = pickle.loads(serialized_data)
    return dictionary

def MessageListener():
    global listeningSocket
    listeningSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listeningSocket.bind(localInfo['procAddr']) #Bind the socket to the local address
    ##cnt = 0
    global done
    #while True and done == 0:
    while True:
        #listeningSocket.settimeout(200.0)
        #print 'trying to recv\n'
        try:
            received_dict = receive_dict_from_socket(listeningSocket)
            #print("Received dictionary:", received_dict)
            #recvMessage = listeningSocket.recv(MAXRECV)
            #print (received_dict)
            MessageHandler(received_dict)
        except socket.timeout:
            print ('did not recv data')
            #done = 1
            continue
    
    print('MessageListener is done')

def MessageHandler(remoteMessage):
    ###remoteMessage = eval(message) #Convert the string we get back to a dictionary
    global localInfo
    if remoteMessage['type'] == REQUEST:
        #print("from Recv Message. Request Type") 
        #print(remoteMessage['procInfo']['procTimestamp']) 
        #print(localInfo['procTimestamp']) 
        #print(localInfo['procState']) 
        if (remoteMessage['procInfo']['procTimestamp'] < localInfo['procTimestamp'] and localInfo['procState'] == WANTED) or localInfo['procState'] == HELD:
            #if DEBUG: print ('Deffered message from --> {0}').format(remoteMessage['procInfo']['procName'])
            defferedQueue.append(remoteMessage['procInfo']['procAddr'])
        else:
            message = { 'type': REPLY, 'procInfo': localInfo}
            #if DEBUG: print('Sent reply to --> {0}').format(remoteMessage['procInfo']['procName'])
            SendMessage(remoteMessage['procInfo']['procAddr'], message)
    
    if remoteMessage['type'] == REPLY:
        #if DEBUG: print ('Reply recieved from --> {0}').format(remoteMessage['procInfo']['procName']) 
        replyQueue.remove(remoteMessage['procInfo']['procAddr'])

##################################################################################################################################
# Mutex Functions                                                                                                               #
##################################################################################################################################
def MutexLock(the_mutex):
    #if DEBUG: print 'Entering --> MutexLock\n'
    global localInfo
    localInfo['procState'] = WANTED             #Change state
    localInfo['procTimestamp'] = time.time()    #Generate the timestamp for the message
    #print("Inside Mutex Lock") 
    #print(localInfo['procTimestamp']) 
    #print(localInfo['procState']) 
    #print(remoteAddresses.values()) 
    requestMessage = { 'type': REQUEST, 'procInfo': localInfo, 'mutex': the_mutex }

    #If we can't send any messages we assume that we are first and therefore can enter the section without any replies
    for address in remoteAddresses.values():
        #print address
        SendMessage(address, requestMessage)
        replyQueue.append(address) #Only add addresses to the replyQueue if we sent a request to someone.
 
    while len(replyQueue) > 0: pass #Wait for the replyQueue to empty before continuing
    #if DEBUG: print 'Exiting  -->  MutexLock'
    localInfo['procState'] = HELD
    print("lock is held now by " +  str(localInfo['procName'])) 
    return True
    
    
def MutexUnlock(the_mutex):
    #if DEBUG: print 'Entering --> MutexUnlock\n'
    localInfo['procState'] = RELEASED
    replyMessage = { 'type': REPLY, 'procInfo': localInfo, 'mutex': the_mutex }
    #for address in replyQueue:
    for address in defferedQueue:
        SendMessage(address, replyMessage)
        defferedQueue.remove(address)
    
    #if DEBUG: print 'Exiting  --> MutexUnlock'
    return True


def MutexExit():
    #if DEBUG: print 'Entering --> MutexExit\n'
    global done
    #global replyQueue
    #global deferredQueue
    global listeningSocket
    #global msgThread
    #global remoteAddresses
    done = done + 1
    #print '\nClosing Listening Socket\n'
    #listeningSocket.close()
    #if DEBUG: print 'Exiting --> MutexExit\n'
    #Stores the information of the local process
    """
    localInfo = { 
                    'procName':         None,
                    'procPID':          None,   
                    'procState':        None,   
                    'procTimestamp':    None,   
                    'procAddr':         None,   
                    'procRemotes':      None 
                }

    defferedQueue = []  #Waiting to reply too
    replyQueue    = []  #Awaiting replies from
    msgThread = None
    listeningSocket = None

    remoteAddresses = { } #Store the addresses of the other processes
    """

    return True