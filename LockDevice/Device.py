import MAC as physicalAddress
import socket
import threading
import json
import time
import sys
import FileName
import picamera
import RPi.GPIO as GPIO


# Distance Function.
def get_distance():
	global Trigger, Echo

	# Issue a singal out.
	GPIO.output(Trigger, True)
	time.sleep(0.00001)
	GPIO.output(Trigger, False)

	while GPIO.input(Echo) == False:
		start = time.time()

	# Get the echo back of the signal. and calculate the time duration.
	while GPIO.input(Echo) == True:
		end = time.time()

	try:
		sig_time = end - start
		# Distance in Inches
		distance = sig_time / 0.000148
		return distance
	except Exception as e:
		print('[*] Exception :: get_distance :: ' + str(e))
		return 100.0


def start_count_down():
	print ('[*] Count down start.')
	for i in range(0, 6):
		time.sleep(1)

		currentDistance = get_distance()
		if currentDistance > 25 or callingBellPressed:
			print("[*] Exit from count down.")
			return

		print('Object now at : {} inch'.format(currentDistance))
	print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Take Image >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")


def keep_safe_distance():
	global sensorThreadStatus, distanceSensing
	while sensorThreadStatus:
		try:
			currentDistance = get_distance()
			if currentDistance < 25 and distanceSensing:
				print('Object Detected at : {} inch'.format(currentDistance))
				start_count_down()
			time.sleep(1)
		except Exception as e:
			print('[*] Exception :: keep_safe_distance :: ' + str(e))
			time.sleep(5)


# Send image function.
# parameter Email, Bell
def sendImage(emailId, email=False, bell=False):
	global host, username

	try:
		# retrive the file name.
		number = str(open('ProgramData/numberFile', 'r').read())
		name = 'imgCL' + number + '.png'

		# creating filename & username JSON object.
		filename = {}
		filename['name'] = name
		filename['username'] = username
		filename['emailId'] = emailId

		if email:
			filename['email'] = 'YES'
			filename['bell'] = 'NO'
		elif bell:
			filename['email'] = 'NO'
			filename['bell'] = 'YES'
		else:
			filename['email'] = 'NO'
			filename['bell'] = 'NO'

		jsonFilename = json.dumps(filename)

		# creating socket object.
		backupServer = socket.socket()

		# connecting to the backup server.
		backupServer.connect((host, 9999))
		# send the JSON objet containing filename and username.
		backupServer.send(str.encode(jsonFilename))
		time.sleep(2)

		# path to the file.
		# and read the file content
		path = 'ProgramData/' + name
		file = open(path, 'rb')
		fileContent = file.read(2048)

		# send the file content until complete.
		while (fileContent):
			backupServer.send(fileContent)
			fileContent = file.read(2048)
		file.close()

		backupServer.close()

	except Exception as e:
		print('[*] Exception :: Image send :: ' + str(e))


# Take image function.
def takeImage(emailId, email=False):
	# initilizing global variables
	global cameraLock, host, username, camera
	print('\n[||] Email :: ' + str(email))
	# locking the camera to prevent another thread to use camera.
	cameraLock.acquire()
	try:
		new_filename = 'ProgramData/' + FileName.get_filename()

		camera.capture(new_filename)

		# checking for email request ot Take image request.
		if email:
			sendImage(emailId, email=True)
		else:
			sendImage(emailId)

	except Exception as e:
		print('[**] Exception :: Take Image function :: ' + str(e))
	finally:
		print('[*] Done')
		# releasing the lock when execution of the method complete.
		cameraLock.release()
		print('\n-' * 5)


# calling Bell Event
def callingBell():
	# global variable of camera lock and
	global cameraLock, bellActivator, host, username
	while bellActivator:
		if GPIO.input(Button) == True:
			print('[*] Calling Bell pressed.')
			cameraLock.acquire()
			try:
				new_filename = 'ProgramData/' + FileName.get_filename()
				camera.capture(new_filename)
				time.sleep(1)

				# sending the image.
				sendImage(None, bell=True)

				print('complete')
			except Exception as e:
				print('[**] Exception :: callingBell :: ' + str(e))
			finally:
				cameraLock.release()


# global veriables.
global username, MAC, host, jsonInfo, cameraLock, doorLock, bellActivator, camera, redLED, Button, Trigger, Echo, sensorThreadStatus, distanceSensing, callingBellPressed

redLED = 19
Button = 26
Trigger = 6
Echo = 13

GPIO.setmode(GPIO.BCM)

GPIO.setup(redLED, GPIO.OUT)
GPIO.setup(Button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(Trigger, GPIO.OUT)
GPIO.setup(Echo, GPIO.IN)

camera = picamera.PiCamera()
camera.vflip = True

# Setting username MAC address Host IPv4 and post number.
username = 'basak'
MAC = physicalAddress.getMACHash()
host = str(sys.argv[1])
post = 9000

bellActivator = True
sensorThreadStatus = True
distanceSensing = True
callingBellPressed = False
# thread locks || one camera lock || one door lock.
doorLock = threading.Lock()
cameraLock = threading.Lock()

callingBellThread = threading.Thread(target=callingBell, name="bell")
keepSafeDistanceThread = threading.Thread(target=keep_safe_distance, name="distance")

# creating identity json
info = {}
info['device'] = 'LockDevice'
info['username'] = username
info['mac'] = MAC
jsonInfo = json.dumps(info)

# socket object.
device = socket.socket()

# connecting to main server
try:
	device.connect((host, post))
	device.send(str.encode(jsonInfo))
except Exception as e:
	print('[**] Exception :: Connecting to Main server :: ' + str(e))

# off/on try catch block.
try:
	# starting calling bell, safe distance thread.
	callingBellThread.start()
	keepSafeDistanceThread.start()
	# main loop for receiving and replying message/request.
	while True:
		try:
			request = device.recv(1024).decode()
			# loads the JSON.
			request = json.loads(request)
			print(request)

		except Exception as e:
			print('[**] Exception :: receiving the data :: ' + str(e))

		# server track JSON.
		# track['request'] = ''
		# track['message'] = 'online'

		# server waiting for.
		# track['message'] = 'online'
		# track['reply'] = 'online'

		if request['message'] == 'online':
			# creating response of online track.
			response = {}
			response['message'] = 'online'
			response['reply'] = 'online'

			# creating JSON response.
			jsonResponse = json.dumps(response)

			# replying to the server.
			device.send(str.encode(jsonResponse))

		# Lock request.
		elif request['request'] == 'Lock':
			print('Requesting for : LOCK')
			GPIO.output(redLED, GPIO.LOW)
			print("Red LED :: OFF")

		# Unlock request.
		elif request['request'] == 'Unlock':
			print('Requesting for : UNLOCK')
			GPIO.output(redLED, GPIO.HIGH)
			print("Red LED :: ON")


		# TakeImage request.
		elif request['request'] == 'TakeImage':
			print('Requesting for : TAKE IMAGE')

			# creating a thread for take image function.
			takeImageFunction = threading.Thread(target=takeImage, args=(request['email'], False),
			                                     name='functionTakeImage')
			takeImageFunction.start()


		# Email request.
		elif request['request'] == 'Email':
			print('Requesting for : EMAIL')
			# creating a thread for Email image.
			emailImageFunction = threading.Thread(target=takeImage, args=(request['email'], True),
			                                      name='functionEmailImage')
			emailImageFunction.start()

except KeyboardInterrupt as e:
	print('\n-' * 5)
	print('[*] Connection closing...')
	device.close()
	time.sleep(0.5)
	# stopping Calling bell loop
	bellActivator = False
	sensorThreadStatus = False
	print('[*] Stopping Program...')
	print('[*] Done. Pres Enter to stop...\n\n')
finally:
	sensorThreadStatus = False
	camera.close()
	GPIO.cleanup()
