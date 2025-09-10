
# === Imports ===
import os
import uuid
from datetime import date
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# === App and Templates ===
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# === Google Sheets Utility ===
CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_JSON", "credentials.json")
SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "Coffee Roaster - Recebimiento")



def get_sheet(work_sheet_name: str):
    """Return a worksheet object by name."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).worksheet(work_sheet_name)


@app.get("/")
def home():
    return {"message": "Welcome to Roasters Café API."}


# === Recebimiento Routes ===
@app.get("/recebimiento", response_class=HTMLResponse)
def form_page(request: Request):
    """Show the Recebimiento form."""
    today = date.today().isoformat()
    defaults = {
        "fecha": today,
        "provedor": "",
        "ciudad": "",
        "origen": "",
        "lote_bolsa": "",
        "cantidad_kg": "",
        "humedad": "",
        "motorista": "",
        "vehiculo_placa": "",
        "observacion": "",
        "libre_contaminacion": "yes",
        "vehiculo_sin_contaminacion": "yes",
        "buen_estado": "yes",
        "responsable": ""
    }
    return templates.TemplateResponse(
        "recebimiento.html",
        {
            "request": request,
            "msg": None,
            "last_submission": None,
            "defaults": defaults
        }
    )


@app.post("/recebimiento", response_class=HTMLResponse)
async def submit_form(
    request: Request,
    fecha: str = Form(...),
    provedor: str = Form(...),
    ciudad: str = Form(""),
    origen: str = Form(""),
    lote_bolsa: str = Form(""),
    cantidad_kg: float = Form(0),
    humedad: float = Form(0),
    motorista: str = Form(""),
    vehiculo_placa: str = Form(""),
    observacion: str = Form(""),
    libre_contaminacion: str = Form(None),
    vehiculo_sin_contaminacion: str = Form(None),
    buen_estado: str = Form(None),
    responsable: str = Form("")
):
    """Handle Recebimiento form submission."""
    sheet = get_sheet("Recebimiento")

    # Set checkbox defaults
    libre_contaminacion = libre_contaminacion if libre_contaminacion == "yes" else "no"
    vehiculo_sin_contaminacion = vehiculo_sin_contaminacion if vehiculo_sin_contaminacion == "yes" else "no"
    buen_estado = buen_estado if buen_estado == "yes" else "no"

    # Generate unique ID
    id_recibimiento = (
        fecha.replace("-", "") + str(provedor[:3]).upper() + str(origen[:3]).upper() + "-" + str(lote_bolsa).upper()
    )

    # Prepare row (ID as first column)
    row = [
        id_recibimiento, fecha, provedor, ciudad, origen, lote_bolsa,
        cantidad_kg, humedad, motorista, vehiculo_placa, observacion,
        libre_contaminacion, vehiculo_sin_contaminacion, buen_estado,
        responsable
    ]

    # Check for duplicate id_recibimiento
    existing_ids = [r[0] for r in sheet.get_all_values()]
    if id_recibimiento in existing_ids:
        msg = f"❌ Ya esta registrado! ID: {id_recibimiento}"
    else:
        sheet.append_row(row)
        msg = f"✅ Registered successfully! ID: {id_recibimiento}"

    last_submission = {
        "id_recibimiento": id_recibimiento,
        "fecha": fecha,
        "provedor": provedor,
        "ciudad": ciudad,
        "origen": origen,
        "lote_bolsa": lote_bolsa,
        "cantidad_kg": cantidad_kg,
        "humedad": humedad,
        "motorista": motorista,
        "vehiculo_placa": vehiculo_placa,
        "observacion": observacion,
        "libre_contaminacion": libre_contaminacion,
        "vehiculo_sin_contaminacion": vehiculo_sin_contaminacion,
        "buen_estado": buen_estado,
        "responsable": responsable
    }
    defaults = {
        "fecha": fecha,
        "provedor": provedor,
        "ciudad": ciudad,
        "origen": origen,
        "lote_bolsa": lote_bolsa,
        "cantidad_kg": cantidad_kg,
        "humedad": humedad,
        "motorista": motorista,
        "vehiculo_placa": vehiculo_placa,
        "observacion": observacion,
        "libre_contaminacion": libre_contaminacion,
        "vehiculo_sin_contaminacion": vehiculo_sin_contaminacion,
        "buen_estado": buen_estado,
        "responsable": responsable
    }
    return templates.TemplateResponse(
        "recebimiento.html",
        {
            "request": request,
            "msg": msg,
            "last_submission": last_submission,
            "defaults": defaults
        }
    )



# === Trillado GET and POST ===
@app.get("/trillado", response_class=HTMLResponse)
def trillado_form_page(request: Request):
    """Show the Trillado form, with ID Recibimiento options from Recebimiento sheet."""
    today = date.today().isoformat()
    sheet_receb = get_sheet("Recebimiento")
    all_rows = sheet_receb.get_all_values()
    recibimiento_ids = [r[0] for r in all_rows[1:]] if len(all_rows) > 1 else []
    defaults = {
        "id_recibimiento": recibimiento_ids[0] if recibimiento_ids else "",
        "fecha": today,
        "grano_num": "",
        "cantidad_kg": "",
        "observacion": ""
    }
    return templates.TemplateResponse(
        "trillado.html",
        {
            "request": request,
            "msg": None,
            "last_submission": None,
            "defaults": defaults,
            "recibimiento_ids": recibimiento_ids
        }
    )


@app.post("/trillado", response_class=HTMLResponse)
async def trillado_submit_form(
    request: Request,
    id_recibimiento: str = Form(...),
    fecha: str = Form(...),
    grano_num: str = Form(...),
    cantidad_kg: float = Form(0),
    observacion: str = Form("")
):
    """Handle Trillado form submission and save to Trillado worksheet."""
    # Get valid IDs for dropdown
    sheet_receb = get_sheet("Recebimiento")
    all_rows = sheet_receb.get_all_values()
    recibimiento_ids = [r[0] for r in all_rows[1:]] if len(all_rows) > 1 else []

    # Save to Trillado worksheet with unique ID Trillado
    sheet_trillado = get_sheet("Trillado")
    id_trillado = f"{id_recibimiento}-{grano_num}"
    # Check for duplicate id_trillado
    trillado_rows = sheet_trillado.get_all_values()
    existing_ids_trillado = [r[-1] for r in trillado_rows[1:]] if len(trillado_rows) > 1 else []
    if id_trillado in existing_ids_trillado:
        msg = f"❌ Ya esta registrado! ID Trillado: {id_trillado}"
    else:
        row = [id_recibimiento, fecha, grano_num, cantidad_kg, observacion, id_trillado]
        sheet_trillado.append_row(row)
        msg = f"✅ Trillado registrado! ID Trillado: {id_trillado}"

    last_submission = {
        "id_recibimiento": id_recibimiento,
        "fecha": fecha,
        "grano_num": grano_num,
        "cantidad_kg": cantidad_kg,
        "observacion": observacion,
        "id_trillado": id_trillado
    }
    defaults = {
        "id_recibimiento": id_recibimiento,
        "fecha": fecha,
        "grano_num": grano_num,
        "cantidad_kg": cantidad_kg,
        "observacion": observacion
    }
    return templates.TemplateResponse(
        "trillado.html",
        {
            "request": request,
            "msg": msg,
            "last_submission": last_submission,
            "defaults": defaults,
            "recibimiento_ids": recibimiento_ids
        }
    )


# === Perfilado GET and POST ===
@app.get("/perfilado", response_class=HTMLResponse)
def perfilado_form_page(request: Request):
    """Show the Perfilado form, with ID Trillado options from Trillado sheet (column F)."""
    sheet_trillado = get_sheet("Trillado")
    trillado_rows = sheet_trillado.get_all_values()
    # Get all IDs from column F (index 5)
    id_trillado_options = [r[5] for r in trillado_rows[1:] if len(r) > 5] if len(trillado_rows) > 1 else []
    defaults = {
        "id_trillado": id_trillado_options[0] if id_trillado_options else "",
        "muestra_pergamino": "",
        "humedad_pergamino": "",
        "muestra_trillado": "",
        "malla": "",
        "densidad": "",
        "humedad_grano_verde": "",
        "negro": "",
        "agrio": "",
        "cereza_seca": "",
        "dano_hongo": "",
        "impurezas": "",
        "dano_severo_insectos": "",
        "parcial_negro": "",
        "parcial_agrio": "",
        "pergamino": "",
        "flotador": "",
        "inmaduro": "",
        "averanado": "",
        "concha": "",
        "partido_mordido": "",
        "cascara_pulpa_seca": "",
        "dano_leve_insectos": "",
        "perfil": "Frutos Citricos",
        "caramelizacion": "",
        "desarrollo": ""
    }
    return templates.TemplateResponse(
        "perfilado.html",
        {
            "request": request,
            "msg": None,
            "last_submission": None,
            "defaults": defaults,
            "id_trillado_options": id_trillado_options
        }
    )


@app.post("/perfilado", response_class=HTMLResponse)
async def perfilado_submit_form(
    request: Request,
    id_trillado: str = Form(...),
    muestra_pergamino: float = Form(0),
    humedad_pergamino: float = Form(0),
    muestra_trillado: float = Form(0),
    malla: str = Form(""),
    densidad: float = Form(0),
    humedad_grano_verde: float = Form(0),
    negro: float = Form(0),
    agrio: float = Form(0),
    cereza_seca: float = Form(0),
    dano_hongo: float = Form(0),
    impurezas: float = Form(0),
    dano_severo_insectos: float = Form(0),
    parcial_negro: float = Form(0),
    parcial_agrio: float = Form(0),
    pergamino: float = Form(0),
    flotador: float = Form(0),
    inmaduro: float = Form(0),
    averanado: float = Form(0),
    concha: float = Form(0),
    partido_mordido: float = Form(0),
    cascara_pulpa_seca: float = Form(0),
    dano_leve_insectos: float = Form(0),
    perfil: str = Form("Frutos Citricos"),
    caramelizacion: float = Form(0),
    desarrollo: float = Form(0)
):
    if muestra_pergamino == 0:
        perda_casca = 0
    else:
        perda_casca = 1 - round(muestra_trillado/muestra_pergamino, 2)
    """Handle Perfilado form submission and save to Perfilado worksheet."""
    # Get valid IDs for dropdown
    sheet_trillado = get_sheet("Trillado")
    trillado_rows = sheet_trillado.get_all_values()
    id_trillado_options = [r[5] for r in trillado_rows[1:] if len(r) > 5] if len(trillado_rows) > 1 else []

    # Save to Perfilado worksheet
    sheet_perfilado = get_sheet("Perfilado")
    # Check for duplicate id_trillado in Perfilado worksheet (column 0)
    perfilado_rows = sheet_perfilado.get_all_values()
    existing_ids_perfilado = [r[0] for r in perfilado_rows[1:]] if len(perfilado_rows) > 1 else []
    if id_trillado in existing_ids_perfilado:
        msg = f"❌ Ya esta registrado! ID Trillado: {id_trillado}"
    else:
        row = [
            id_trillado, muestra_pergamino, humedad_pergamino, muestra_trillado, malla, densidad, humedad_grano_verde,perda_casca,
            negro, agrio, cereza_seca, dano_hongo, impurezas, dano_severo_insectos, parcial_negro, parcial_agrio,
            pergamino, flotador, inmaduro, averanado, concha, partido_mordido, cascara_pulpa_seca, dano_leve_insectos,
            perfil, caramelizacion, desarrollo
        ]
        sheet_perfilado.append_row(row)
        msg = f"✅ Perfilado registrado! ID Trillado: {id_trillado}"

    last_submission = {
        "id_trillado": id_trillado,
        "muestra_pergamino": muestra_pergamino,
        "humedad_pergamino": humedad_pergamino,
        "muestra_trillado": muestra_trillado,
        "malla": malla,
        "densidad": densidad,
        "humedad_grano_verde": humedad_grano_verde,
        "negro": negro,
        "agrio": agrio,
        "cereza_seca": cereza_seca,
        "dano_hongo": dano_hongo,
        "impurezas": impurezas,
        "dano_severo_insectos": dano_severo_insectos,
        "parcial_negro": parcial_negro,
        "parcial_agrio": parcial_agrio,
        "pergamino": pergamino,
        "flotador": flotador,
        "inmaduro": inmaduro,
        "averanado": averanado,
        "concha": concha,
        "partido_mordido": partido_mordido,
        "cascara_pulpa_seca": cascara_pulpa_seca,
        "dano_leve_insectos": dano_leve_insectos,
        "perfil": perfil,
        "caramelizacion": caramelizacion,
        "desarrollo": desarrollo
    }
    defaults = last_submission.copy()
    return templates.TemplateResponse(
        "perfilado.html",
        {
            "request": request,
            "msg": msg,
            "last_submission": last_submission,
            "defaults": defaults,
            "id_trillado_options": id_trillado_options
        }
    )

