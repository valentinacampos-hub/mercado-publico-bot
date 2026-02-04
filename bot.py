import time
import json
import os
import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import gspread
from oauth2client.service_account import ServiceAccountCredentials


# ==========================================
# CONFIGURACIÓN
# ==========================================

RUT_BUSCAR = "60803000-K"   # 👈 CAMBIA AQUÍ TU RUT
NOMBRE_HOJA = "historial"


# ==========================================
# AUTENTICACIÓN GOOGLE SHEETS
# ==========================================

def conectar_google_sheets():

    print("Conectando con Google Sheets...")

    creds_json = os.environ["GOOGLE_CREDENTIALS"]
    creds_dict = json.loads(creds_json)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    cliente = gspread.authorize(creds)

    sheet = cliente.open("MercadoPublico").worksheet(NOMBRE_HOJA)

    print("Conexión exitosa con Google Sheets ✅")

    return sheet


# ==========================================
# EJECUTAR BÚSQUEDA EN MERCADO PÚBLICO
# ==========================================

def ejecutar_busqueda():

    print("Iniciando Selenium...")

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 25)

    try:
        print("Accediendo a Mercado Público...")
        driver.get("https://www.mercadopublico.cl/Home")

        time.sleep(5)

        print("Marcando checkbox Comprador...")
        chk = wait.until(EC.element_to_be_clickable((By.ID, "chkComprador")))
        driver.execute_script("arguments[0].click();", chk)

        print("Abriendo modal de búsqueda...")
        boton = wait.until(EC.element_to_be_clickable((By.ID, "btnBuscarComprador")))
        boton.click()

        print("Buscando por RUT...")
        input_rut = wait.until(EC.presence_of_element_located((By.ID, "txtRut")))
        input_rut.clear()
        input_rut.send_keys(RUT_BUSCAR)

        time.sleep(2)

        print("Seleccionando primer resultado...")
        resultado = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".ui-menu-item")))
        resultado.click()

        print("Ejecutando búsqueda final...")
        buscar = wait.until(EC.element_to_be_clickable((By.ID, "btnBuscar")))
        buscar.click()

        time.sleep(8)

        print("Extrayendo resultados...")

        datos = []

        for i in range(1, 4):

            try:
                base = f"rptResultados_ctl0{i}"

                numero = driver.find_element(By.ID, f"{base}_lblCodigo").text
                nombre = driver.find_element(By.ID, f"{base}_lblNombre").text
                comprador = driver.find_element(By.ID, f"{base}_lblComprador").text
                fecha = driver.find_element(By.ID, f"{base}_lblFecha").text
                estado = driver.find_element(By.ID, f"{base}_lblEstado").text

                datos.append({
                    "numero": numero.strip(),
                    "nombre": nombre.strip(),
                    "comprador": comprador.strip(),
                    "fecha_cierre": fecha.strip(),
                    "estado": estado.strip()
                })

            except Exception:
                break

        print(f"Se extrajeron {len(datos)} resultados.")

        return datos

    finally:
        driver.quit()


# ==========================================
# GUARDAR EN GOOGLE SHEETS
# ==========================================

def guardar_en_sheets(sheet, resultados):

    print("Leyendo historial existente...")

    existentes = sheet.get_all_records()

    numeros_existentes = [fila["número"] for fila in existentes]

    nuevos = []

    for r in resultados:
        if r["numero"] not in numeros_existentes:
            nuevos.append(r)

    if not nuevos:
        print("No hay licitaciones nuevas.")
        return []

    print(f"Se encontraron {len(nuevos)} licitaciones NUEVAS 🔔")

    fecha_actual = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    for r in nuevos:

        sheet.append_row([
            fecha_actual,
            r["numero"],
            r["nombre"],
            r["comprador"],
            r["fecha_cierre"],
            r["estado"]
        ])

    print("Nuevos registros guardados en Google Sheets ✅")

    return nuevos


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

def main():

    resultados = ejecutar_busqueda()

    if not resultados:
        print("No se obtuvieron resultados desde Mercado Público.")
        return

    sheet = conectar_google_sheets()

    nuevos = guardar_en_sheets(sheet, resultados)

    if nuevos:

        print("\n📢 LICITACIONES NUEVAS DETECTADAS:\n")

        for r in nuevos:
            print(f"- {r['numero']} | {r['nombre']} | {r['fecha_cierre']}")

    else:
        print("\nSin novedades por ahora 🙂")


if __name__ == "__main__":
    main()
