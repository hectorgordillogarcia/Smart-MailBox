# -- coding:utf-8 --
import RPi.GPIO as GPIO
import requests
import time
from datetime import datetime
import subprocess  # <-- Añadido para usar libcamera-still
import os  # <-- Para comprobar si la imagen existe

# Configuración de Telegram
BOT_TOKEN = '8108976789:AAGjiGkqmI8ioUSGWjQF6-J6GMJMS1fkCBE'
CHAT_ID = '1388182140'
API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'


def mover_servo(angulo):
    duty = 2 + (angulo / 18)
    servo.ChangeDutyCycle(duty)
    time.sleep(1.5)
    servo.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo.ChangeDutyCycle(0)

# Estado del buzón
estado_buzon = "abierto"
# Asegura que el buzón esté realmente abierto al arrancar


if estado_buzon != "abierto":
    mover_servo(0)
    estado_buzon = "abierto"
    print("Buzón estaba cerrado. Se ha abierto al iniciar.")
else:
    print("Buzón ya estaba abierto al iniciar.")


# Pines
PIR_PIN = 17
SERVO_PIN = 18
LED_PIN = 24

# Configuración GPIO
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

# Configurar PWM
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

def encender_flash():
    GPIO.output(LED_PIN, GPIO.HIGH)
    print('Encendiendo LED')
    
def apagar_flash():
    GPIO.output(LED_PIN, GPIO.LOW)
    print('Apagando LED')

def movimiento_detectado(pin):
    global estado_buzon
    if estado_buzon == "cerrado":
        fecha = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
        enviar_mensaje(f"Se ha detectado movimiento en el buzón!\n{fecha}")
        encender_flash()
        capturar_y_enviar_foto()
        apagar_flash()
    time.sleep(15)
    print("Tiempo de espera entre carta y carta finalizado")


GPIO.remove_event_detect(PIR_PIN)
GPIO.add_event_detect(PIR_PIN, GPIO.RISING, callback=movimiento_detectado, bouncetime=200)

def enviar_mensaje(mensaje):
    try:
        response = requests.post(f'{API_URL}/sendMessage', json={
            'chat_id': CHAT_ID,
            'text': mensaje
        })
        print("Mensaje enviado:", response.text)
    except Exception as e:
        print("Error al enviar mensaje:", e)

def enviar_foto(ruta):
    try:
        with open(ruta, 'rb') as foto:
            response = requests.post(f'{API_URL}/sendPhoto', files={'photo': foto}, data={'chat_id': CHAT_ID})
        print("Foto enviada:", response.text)
    except Exception as e:
        print("Error al enviar la foto:", e)

def capturar_y_enviar_foto():
    nombre_archivo = '/home/pi/foto_buzon.jpg'
    try:
        # Captura con libcamera
        subprocess.run(['libcamera-still', '-o', nombre_archivo, '-t', '1000', '--width', '1280', '--height', '720'], check=True)
        print("Foto capturada.")
        if os.path.exists(nombre_archivo):
            enviar_foto(nombre_archivo)
    except Exception as e:
        print("Error al capturar/enviar la foto:", e)



def revisar_comandos():
    global estado_buzon, last_update_id
    try:
        response = requests.get(f'{API_URL}/getUpdates', params={'offset': last_update_id + 1})
        data = response.json()

        if not data["ok"]:
            return

        for update in data["result"]:
            last_update_id = update["update_id"]
            if "message" in update and "text" in update["message"]:
                texto = update["message"]["text"].strip().lower()

                if texto in ["abre", "/abrir"]:
                    if estado_buzon == "abierto":
                        enviar_mensaje("El buzón ya está abierto.")
                    else:
                        mover_servo(0)
                        estado_buzon = "abierto"
                        enviar_mensaje("Buzón abierto.")

                elif texto in ["cierra", "/cerrar"]:
                    if estado_buzon == "cerrado":
                        enviar_mensaje("El buzón ya está cerrado.")
                    else:
                        mover_servo(90)
                        estado_buzon = "cerrado"
                        enviar_mensaje("Buzón cerrado.")

                elif texto in ["estado", "/estado"]:
                    enviar_mensaje(f"El buzón está {estado_buzon}.")

                elif texto == "/foto":
                    enviar_mensaje("Foto solicitada. Capturando...")
                    encender_flash()
                    capturar_y_enviar_foto()
                    apagar_flash()
    except Exception as e:
        print("Error revisando comandos:", e)

last_update_id = 0
apagar_flash()

print("Sistema iniciado. Esperando comandos y movimiento...")

try:
    while True:
        revisar_comandos()
        time.sleep(1)

except KeyboardInterrupt:
    print("Saliendo...")

finally:
    servo.stop()
    GPIO.cleanup()
