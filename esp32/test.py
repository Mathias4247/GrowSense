from machine import Pin, ADC
from neopixel import NeoPixel
from time import sleep
import _thread

VANDP = Pin(27, Pin.OUT)

LDR = ADC(Pin(39))

LDR.width(ADC.WIDTH_12BIT)
LDR.atten(ADC.ATTN_11DB)

LED = 32
antal_led = 22

led_lys = NeoPixel(Pin(LED), antal_led)


fugt1 = ADC(Pin(35))
fugt1.width(ADC.WIDTH_12BIT)
fugt1.atten(ADC.ATTN_11DB)


fugt2 = ADC(Pin(34))
fugt2.width(ADC.WIDTH_12BIT)
fugt2.atten(ADC.ATTN_11DB)

vandstand = Pin(12, Pin.IN)

def set_color(r, g, b):
    for i in range(antal_led):
        led_lys[i] = (r, g, b)
        led_lys.write()
               
def måling():
    while True:
        adc = LDR.read()
        adc1 = fugt1.read()
        adc2 = fugt2.read()
        print(f"LDR {adc}")
        print(f"fugt1 {adc1}")
        print(f"fugt2 {adc2}")
        print(vandstand.value())
        sleep(1)

def pumpe():
    while True:
        VANDP.off()
        sleep(5)
        VANDP.on()
        sleep(1)
    
set_color(255, 255, 255)

_thread.start_new_thread(måling, ())
_thread.start_new_thread(pumpe, ())
    
    
    
    
    

