import serial, time
ser = serial.Serial("/dev/serial0", 115200, timeout=1)
ser.write(b"bøsse\n")
time.sleep(0.2)
print("modtaget:", ser.readline())
