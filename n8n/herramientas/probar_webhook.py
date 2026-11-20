"""
Prueba el webhook de producción del chat (flujo 00) con una o varias preguntas, igual que lo hace la app Android.

Lee N8N_WEBHOOK_URL y CHAT_TOKEN del .env de la raíz y no los imprime.

Uso (desde la raíz del proyecto):
    python n8n/herramientas/probar_webhook.py "U00134229|¿Qué competencias digitales me faltan?" "U00100004|¿Cuántas horas libres tengo?"
Cada argumento es CODIGO|pregunta. Cada pregunta usa una sesión nueva (sin memoria previa).
Las acciones directas de la app se piden con @: "U00179961|@perfil" (ficha del estudiante) y "U00179961|@noticias"
(noticias del día).
"""
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def leer_env() -> dict:
    datos = {}
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            datos[k.strip()] = v.strip()
    return datos


def preguntar(env: dict, codigo: str, mensaje: str) -> tuple[dict, float]:
    datos = {"estudiante_codigo": codigo, "session_id": "prueba-" + uuid.uuid4().hex[:8]}
    if mensaje.startswith("@"):
        datos["accion"] = mensaje[1:]
    else:
        datos["mensaje"] = mensaje
    cuerpo = json.dumps(datos).encode()
    req = urllib.request.Request(env["N8N_WEBHOOK_URL"], data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json", "X-Chat-Token": env["CHAT_TOKEN"]})
    inicio = time.time()
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode()), time.time() - inicio


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    env = leer_env()
    for arg in sys.argv[1:]:
        codigo, mensaje = arg.split("|", 1)
        d, segundos = preguntar(env, codigo.strip(), mensaje.strip())
        if "perfil" in d:
            p = d["perfil"]
            print(f"== {codigo} | accion perfil  [{segundos:.1f}s]")
            print(f"{p['nombre']} | {p['programa']} | semestre {p["semestre_actual"]} | avance {p['avance']['porcentaje_avance']}%"
                  f" de {p['avance']['creditos_totales']} créditos")
            print("horario:", [h["curso"] for h in p.get("horario", [])])
            print()
            continue
        if "noticias" in d:
            n = d["noticias"]
            print(f"== {codigo} | accion noticias  [{segundos:.1f}s]")
            print(f"{n['total']} noticias, {n['de_hoy']} de hoy ({n['fecha_consulta']}), categorías: {n['categorias']}")
            for x in n["noticias"][:5]:
                print(f"  {'HOY ' if x['es_hoy'] else ''}{x['fecha'][:10]} [{x['categoria']}] {x['titulo'][:70]} | {x['fuente']}")
            print()
            continue
        print(f"== {codigo} | {mensaje}  [{d.get('intencion')}, {segundos:.1f}s]")
        print(d.get("respuesta"))
        print("fuentes:", [f["titulo"] for f in d.get("fuentes", [])])
        print()


if __name__ == "__main__":
    main()
