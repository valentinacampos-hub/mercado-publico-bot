import google_colab_selenium as gs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# =============== CONFIGURACIÓN ===============

RUT = "61.980.230-6"
GOOGLE_SHEET_NAME = "Licitaciones MP"

# =============== AUTENTICACIÓN GOOGLE SHEETS ===============

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)

sheet = client.open(GOOGLE_SHEET_NAME).worksheet("historial")

# =============== FUNCIONES ===============

def obtener_historial():
    try:
        datos = sheet.get_all_records()
        return [fila["numero"] for fila in datos]
    except:
        return []

def guardar_resultados(resultados):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for r in resultados:
        sheet.append_row([
            fecha,
            r["numero"],
            r["nombre"],
            r["comprador"],
            r["fecha"],
            r["estado"]
        ])

def detectar_nuevas(resultados, historial):
    nuevas = []
    for r in resultados:
        if r["numero"] not in historial:
            nuevas.append(r)
    return nuevas

# =============== INICIO SELENIUM ===============

driver = gs.UndetectedChromeDriver()
wait = WebDriverWait(driver, 40)

try:
    print("Accediendo a Mercado Público...")
    driver.get("https://www.mercadopublico.cl/portal/Modules/Site/Busquedas/BuscadorAvanzado.aspx?qs=1")
    time.sleep(6)

    print("Marcando checkbox Comprador a Buscar...")

    chk = wait.until(EC.element_to_be_clickable((By.ID, "chkComprador")))
    if not chk.is_selected():
        chk.click()

    print("Abriendo modal de búsqueda...")

    btn_comprador = wait.until(
        EC.element_to_be_clickable((By.ID, "btnComprador"))
    )
    driver.execute_script("arguments[0].click();", btn_comprador)

    print("Modal abierto correctamente.")

    input_run = wait.until(
        EC.visibility_of_element_located((By.NAME, "txtTaxId"))
    )

    input_run.clear()

    for char in RUT:
        input_run.send_keys(char)
        time.sleep(0.1)

    btn_search_modal = driver.find_element(By.NAME, "btnSearchComprador")
    driver.execute_script("arguments[0].click();", btn_search_modal)

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

    driver.execute_script("arguments[0].click();", btn_buscar)

    print("Cargando resultados finales...")
    time.sleep(10)

    print("\nExtrayendo TEXTO desde la ventana de resultados...\n")

    filas = driver.find_elements(By.CSS_SELECTOR,
        "tr.cssGridAdvancedSearch, tr.cssGridAdvancedSearchAlter"
    )

    print(f"Filas encontradas: {len(filas)}")

    resultados = []

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
        print("---------------")
        print("Número   :", r["numero"])
        print("Nombre   :", r["nombre"])
        print("Comprador:", r["comprador"])
        print("Fecha    :", r["fecha"])
        print("Estado   :", r["estado"])

    # =============== PROCESO GOOGLE SHEETS ===============

    historial = obtener_historial()

    nuevas = detectar_nuevas(resultados, historial)

    guardar_resultados(resultados)

    print("\nDatos guardados en Google Sheets correctamente ✅")

    # =============== MENSAJE ALERTA ===============

    if nuevas:
        print("\n🚨 SE DETECTARON LICITACIONES NUEVAS 🚨\n")

        mensaje = "📢 NUEVAS LICITACIONES DETECTADAS\n\n"

        for n in nuevas:
            mensaje += f"🔹 {n['numero']}\n"
            mensaje += f"{n['nombre']}\n"
            mensaje += f"📅 {n['fecha']} - {n['estado']}\n\n"

        print(mensaje)

    else:
        print("\nNo hay licitaciones nuevas desde la última ejecución.")

    print("\nProceso finalizado correctamente ✅")

except Exception as e:
    driver.save_screenshot("error_debug.png")
    print(f"\nERROR: {str(e)}")
    print("Se guardó 'error_debug.png' para revisar.")

finally:
    driver.quit()
