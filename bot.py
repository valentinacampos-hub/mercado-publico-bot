import os
import json
import time
from datetime import datetime

import google_colab_selenium as gs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# ===== CONFIGURACIÓN =====

RUT = "61.980.230-6"

SPREADSHEET_ID = "TU_ID_DE_GOOGLE_SHEETS_AQUÍ"
HOJA = "historial"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

ARCHIVO_CREDENCIALES = "credenciales.json"


# ===== CONEXIÓN A GOOGLE SHEETS =====

def conectar_sheets():

    # Si existe variable de entorno (GitHub Actions)
    if "GOOGLE_CREDENTIALS" in os.environ:
        print("Usando credenciales desde variable de entorno")

        creds_json = os.environ["GOOGLE_CREDENTIALS"]
        creds_info = json.loads(creds_json)

        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=SCOPES
        )

    else:
        print("Usando archivo credenciales.json local")

        creds = Credentials.from_service_account_file(
            ARCHIVO_CREDENCIALES,
            scopes=SCOPES
        )

    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()


# ===== LEER HISTORIAL =====

def leer_historial(sheets):

    rango = f"{HOJA}!A:F"

    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=rango
        ).execute()

        valores = result.get("values", [])

        return valores

    except Exception as e:
        print("Error leyendo historial:", e)
        return []


# ===== GUARDAR NUEVOS RESULTADOS =====

def guardar_resultados(sheets, nuevos):

    rango = f"{HOJA}!A:F"

    body = {
        "values": nuevos
    }

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=rango,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    print(f"Se guardaron {len(nuevos)} filas nuevas en Google Sheets")


# ===== EJECUTAR BÚSQUEDA EN MERCADO PÚBLICO =====

def ejecutar_busqueda():

    print("Iniciando Selenium...")

    driver = gs.UndetectedChromeDriver()
    wait = WebDriverWait(driver, 40)

    resultados = []

    try:
        print("Accediendo a Mercado Público...")
        driver.get(
            "https://www.mercadopublico.cl/portal/Modules/Site/Busquedas/BuscadorAvanzado.aspx?qs=1"
        )

        time.sleep(7)

        print("Marcando checkbox Comprador...")

        chk = wait.until(
            EC.element_to_be_clickable((By.ID, "chkComprador"))
        )
        if not chk.is_selected():
            chk.click()

        print("Abriendo modal de búsqueda...")

        btn = wait.until(
            EC.element_to_be_clickable((By.ID, "btnComprador"))
        )
        btn.click()

        print("Modal abierto correctamente.")

        input_run = wait.until(
            EC.visibility_of_element_located((By.NAME, "txtTaxId"))
        )

        input_run.clear()

        for char in RUT:
            input_run.send_keys(char)
            time.sleep(0.1)

        time.sleep(1)

        driver.find_element(By.NAME, "btnSearchComprador").click()

        print("RUT buscado.")

        org_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span[id*='lblOrganizationName']"))
        )
        org_link.click()

        print("Organización seleccionada.")

        try:
            wait.until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except:
            pass

        print("Ejecutando búsqueda final...")

        btn_buscar = wait.until(
            EC.element_to_be_clickable((By.NAME, "btnBusqueda"))
        )
        btn_buscar.click()

        print("Cargando resultados finales...")
        time.sleep(10)

        print("Extrayendo TEXTO desde la ventana de resultados...")

        filas = driver.find_elements(
            By.CSS_SELECTOR,
            "tr.cssGridAdvancedSearch, tr.cssGridAdvancedSearchAlter"
        )

        for fila in filas[:3]:

            columnas = fila.find_elements(By.TAG_NAME, "td")

            if len(columnas) >= 5:
                numero = columnas[0].text.strip()
                nombre = columnas[1].text.strip()
                comprador = columnas[2].text.strip()
                fecha_cierre = columnas[3].text.strip()
                estado = columnas[4].text.strip()

                resultados.append({
                    "numero": numero,
                    "nombre": nombre,
                    "comprador": comprador,
                    "fecha_cierre": fecha_cierre,
                    "estado": estado
                })

        return resultados

    except Exception as e:
        print("ERROR EN SELENIUM:", e)
        driver.save_screenshot("error.png")
        return []

    finally:
        driver.quit()


# ===== PROCESO PRINCIPAL =====

def main():

    sheets = conectar_sheets()

    print("Leyendo historial existente...")
    historial = leer_historial(sheets)

    numeros_previos = [fila[1] for fila in historial[1:]] if len(historial) > 1 else []

    print("Ejecutando búsqueda en Mercado Público...")
    datos = ejecutar_busqueda()

    if not datos:
        print("No se encontraron resultados")
        return

    nuevos = []

    for d in datos:

        if d["numero"] not in numeros_previos:

            fila = [
                datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                d["numero"],
                d["nombre"],
                d["comprador"],
                d["fecha_cierre"],
                d["estado"]
            ]

            nuevos.append(fila)

    if nuevos:
        print(f"Se detectaron {len(nuevos)} licitaciones nuevas")
        guardar_resultados(sheets, nuevos)

    else:
        print("No hay licitaciones nuevas")

    print("Proceso finalizado correctamente")


if __name__ == "__main__":
    main()
