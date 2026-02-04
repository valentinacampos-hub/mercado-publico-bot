import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ==============================
# CONFIGURACIÓN
# ==============================

RUT_BUSCAR = "61.980.230-6"

SPREADSHEET_ID = "1s1XwpGs1XDggSaUOi0_0jA6Z2sLXYBk4lkDU0aZlkc4"
HOJA = "historial"

ARCHIVO_CREDENCIALES = "credenciales.json"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ==============================
# GOOGLE SHEETS
# ==============================

def conectar_sheets():
    creds = Credentials.from_service_account_file(
        ARCHIVO_CREDENCIALES,
        scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()


def leer_historial(sheets):
    rango = f"{HOJA}!A2:F"

    result = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=rango
    ).execute()

    valores = result.get("values", [])

    return {fila[1] for fila in valores if len(fila) > 1}


def guardar_resultados(sheets, resultados):
    rango = f"{HOJA}!A:F"

    valores = []

    for r in resultados:
        valores.append([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            r["numero"],
            r["nombre"],
            r["comprador"],
            r["fecha_cierre"],
            r["estado"]
        ])

    body = {"values": valores}

    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=rango,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()


# ==============================
# SELENIUM - EXTRACCIÓN
# ==============================

def ejecutar_busqueda():

    print("Iniciando Selenium...")

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 40)

    try:
        print("Accediendo al Buscador Avanzado...")
        driver.get("https://www.mercadopublico.cl/portal/Modules/Site/Busquedas/BuscadorAvanzado.aspx?qs=1")

        time.sleep(8)

        print("Marcando checkbox Comprador...")

        chk = wait.until(
            EC.element_to_be_clickable((By.ID, "chkComprador"))
        )
        driver.execute_script("arguments[0].click();", chk)

        time.sleep(2)

        print("Abriendo modal de búsqueda de comprador...")

        btn = wait.until(
            EC.element_to_be_clickable((By.ID, "btnComprador"))
        )
        driver.execute_script("arguments[0].click();", btn)

        print("Modal abierto.")

        input_rut = wait.until(
            EC.visibility_of_element_located((By.NAME, "txtTaxId"))
        )

        input_rut.clear()
        input_rut.send_keys(RUT_BUSCAR)

        time.sleep(2)

        btn_search = driver.find_element(By.NAME, "btnSearchComprador")
        driver.execute_script("arguments[0].click();", btn_search)

        print("RUT ingresado y buscado.")

        org = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "span[id*='lblOrganizationName']"))
        )
        org.click()

        print("Organización seleccionada.")

        time.sleep(3)

        print("Ejecutando búsqueda final...")

        btn_buscar = wait.until(
            EC.element_to_be_clickable((By.NAME, "btnBusqueda"))
        )

        driver.execute_script("arguments[0].click();", btn_buscar)

        print("Esperando resultados...")

        time.sleep(10)

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

    except Exception as e:
        driver.save_screenshot("error.png")
        print("Error detectado. Se guardó captura error.png")
        raise e

    finally:
        driver.quit()


# ==============================
# PROCESO PRINCIPAL
# ==============================

def main():

    sheets = conectar_sheets()

    print("Leyendo historial existente...")
    historial = leer_historial(sheets)

    print("Ejecutando búsqueda en Mercado Público...")
    resultados = ejecutar_busqueda()

    nuevas = []

    for r in resultados:
        if r["numero"] not in historial:
            nuevas.append(r)

    print(f"Licitaciones nuevas detectadas: {len(nuevas)}")

    if nuevas:
        print("Guardando nuevas licitaciones en Google Sheets...")
        guardar_resultados(sheets, nuevas)
        print("Guardado exitoso.")

    print("\n=== RESUMEN ===")
    for r in resultados:
        print(f"- {r['numero']} | {r['nombre']}")

    print("\nProceso finalizado correctamente.")


if __name__ == "__main__":
    main()
