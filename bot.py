import google_colab_selenium as gs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ========== CONFIGURACIÓN ==========

RUT = "61.980.230-6"

GOOGLE_SHEET_NAME = "historial"

# ===================================

def conectar_sheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credenciales.json", scope
    )

    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1

    return sheet


def obtener_codigos_existentes(sheet):
    datos = sheet.get_all_records()

    codigos = [fila["número"] for fila in datos]

    return codigos


def guardar_resultados_en_sheets(resultados):
    sheet = conectar_sheets()

    existentes = obtener_codigos_existentes(sheet)

    nuevos = 0

    for r in resultados:
        if r["numero"] not in existentes:

            fila = [
                datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                r["numero"],
                r["nombre"],
                r["comprador"],
                r["fecha"],
                r["estado"]
            ]

            sheet.append_row(fila)
            nuevos += 1

    print(f"Se agregaron {nuevos} licitaciones nuevas a Google Sheets.")


def ejecutar_busqueda():
    driver = gs.UndetectedChromeDriver()
    wait = WebDriverWait(driver, 40)

    resultados = []

    try:
        print("Accediendo a Mercado Público...")
        driver.get("https://www.mercadopublico.cl/portal/Modules/Site/Busquedas/BuscadorAvanzado.aspx?qs=1")

        time.sleep(7)

        print("Marcando checkbox Comprador a Buscar...")

        chk = wait.until(
            EC.presence_of_element_located((By.ID, "chkComprador"))
        )

        driver.execute_script("arguments[0].click();", chk)

        print("Abriendo modal de búsqueda...")

        btn = wait.until(
            EC.element_to_be_clickable((By.ID, "btnComprador"))
        )

        driver.execute_script("arguments[0].click();", btn)

        print("Modal abierto correctamente.")

        input_run = wait.until(
            EC.visibility_of_element_located((By.NAME, "txtTaxId"))
        )

        input_run.clear()

        for char in RUT:
            input_run.send_keys(char)
            time.sleep(0.1)

        time.sleep(1)

        btn_search_modal = driver.find_element(By.NAME, "btnSearchComprador")
        driver.execute_script("arguments[0].click();", btn_search_modal)

        print("RUT buscado.")

        org_link = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span[id*='lblOrganizationName']"))
        )

        org_link.click()

        print("Organización seleccionada.")

        time.sleep(2)

        btn_buscar = wait.until(
            EC.element_to_be_clickable((By.NAME, "btnBusqueda"))
        )

        driver.execute_script("arguments[0].click();", btn_buscar)

        print("Cargando resultados finales...")
        time.sleep(10)

        print("Extrayendo TEXTO desde la ventana de resultados...")

        filas = driver.find_elements(
            By.CSS_SELECTOR,
            "tr.cssGridAdvancedSearch, tr.cssGridAdvancedSearchAlter"
        )

        print("Filas encontradas:", len(filas))

        for fila in filas[:3]:
            columnas = fila.find_elements(By.TAG_NAME, "td")

            if len(columnas) >= 5:
                resultados.append({
                    "numero": columnas[0].text.strip(),
                    "nombre": columnas[1].text.strip(),
                    "comprador": columnas[2].text.strip(),
                    "fecha": columnas[3].text.strip(),
                    "estado": columnas[4].text.strip()
                })

        print("\n=== RESULTADOS EXTRAÍDOS ===\n")

        for r in resultados:
            print(r)

        return resultados

    except Exception as e:
        print("ERROR DURANTE EJECUCIÓN:", str(e))
        return []

    finally:
        driver.quit()


if __name__ == "__main__":

    datos = ejecutar_busqueda()

    if datos:
        guardar_resultados_en_sheets(datos)
    else:
        print("No se encontraron resultados para guardar.")
