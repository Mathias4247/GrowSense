from machine import Pin, ADC
from neopixel import NeoPixel
from time import sleep

LDR_ADC = ADC(Pin(32))

LDR_ADC.width(ADC.WIDTH_12BIT)
LDR_ADC.atten(ADC.ATTN_11DB)

GPIO_LED = 33
AMOUNT_LED = 22

LYS = NeoPixel(Pin(GPIO_LED), AMOUNT_LED)

#1:4:1 skaleret
#seedling_profile = (25, 100, 25)

SEEDLING_PROFILE = (25,100,25)

#r = 30,6 * 100/44 = 69,5 : g = 44 * 100/44 = 100 : b = 25.4 * 100/44 = 57.7 (skaleret)
#standard_profile = (70, 100, 58)

STANDARD_PROFILE = (70,100,58)

def set_color(r, g, b):
    r = int((r/100) * 255)
    g = int((g/100) * 255)
    b = int((b/100) * 255)
    for i in range(AMOUNT_LED):
        LYS[i] = (r, g, b)
    LYS.write()

#spændingsdeler med LDR i top og 300 ohms modstand i bund (ADC stiger med mere lys)
#solskinsdag udenfor: ADC = 3200, lx = 145000
#sol, men i skygge: ADC = 1615, lx = 4000
#fuld mørke (under en jakke): ADC = 0, lx = 0

ADC_DARK = 0
ADC_BRIGHT = 1615

LED_DARK = 100
LED_BRIGHT = 0

a = (LED_BRIGHT - LED_DARK) / (ADC_BRIGHT - ADC_DARK)
b = LED_DARK - a * ADC_DARK

def light_control():
    adc = LDR_ADC.read()
    brightness = a * adc + b

    if brightness < 0:
        brightness = 0
    elif brightness > 100:
        brightness = 100
        
    print("ADC:", adc)
    print("LED %:", brightness)
    
    set_color(brightness, brightness, brightness)

try:
    while True:
        light_control()
        sleep(0.5)

except KeyboardInterrupt:
    set_color(0,0,0)