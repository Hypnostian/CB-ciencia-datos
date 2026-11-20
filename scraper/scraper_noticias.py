#!/usr/bin/env python3
"""Scraper de noticias del día (misma lógica que el workflow n8n 04_noticias_scraper).

Recoge noticias de educación, tecnología e ingeniería de sistemas, cada una con su fuente y su fecha, y las guarda
(upsert por url) en la tabla `noticias` de Supabase, o imprime JSON con --json. Fuentes (FUENTES):
  - UNAB (API pública de WordPress de unab.edu.co): Ingeniería de Sistemas, Oferta educativa, Educación Continua
    y Estudiantes.
  - El Tiempo (RSS): Educación y Tecnósfera.
  - Google Noticias (RSS de búsqueda): "ingeniería de sistemas" o "desarrollo de software" en Colombia, última semana.
    La fuente que se guarda es el medio que publicó la noticia.

En n8n corre solo cada 6 horas (Schedule Trigger); este script sirve para probarlo o cargarlo desde la terminal.

Uso:
  python scraper_noticias.py --json                 # solo imprime JSON (no toca la BD)
  python scraper_noticias.py --json --salida muestra_noticias.json
  python scraper_noticias.py --hoy                  # muestra en la terminal solo las noticias de hoy
  DATABASE_URL=postgresql://... python scraper_noticias.py   # upsert en Supabase
"""
import argparse
import html
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

USER_AGENT = "CBDatos-NoticiasBot/1.0 (proyecto academico UNAB; consulta de baja frecuencia)"
RESUMEN_MAX = 500
ZONA_CO = timezone(timedelta(hours=-5))  # Colombia no tiene horario de verano
WP = "https://unab.edu.co/wp-json/wp/v2/posts?per_page=10&orderby=date&order=desc&_fields=date,link,title,excerpt&categories="
GOOGLE = ("https://news.google.com/rss/search?q=%22ingenier%C3%ADa+de+sistemas%22+OR+%22desarrollo+de+software%22"
          "+when:7d&hl=es-419&gl=CO&ceid=CO:es-419")

# tipo, categoría temática, fuente, url
FUENTES = [
    ("wordpress", "Ingeniería de Sistemas", "UNAB", WP + "556"),
    ("wordpress", "Educación", "UNAB", WP + "20"),
    ("wordpress", "Educación", "UNAB", WP + "430"),
    ("wordpress", "Vida UNAB", "UNAB", WP + "232"),
    ("rss", "Educación", "El Tiempo", "https://www.eltiempo.com/rss/vida_educacion.xml"),
    ("rss", "Tecnología", "El Tiempo", "https://www.eltiempo.com/rss/tecnosfera.xml"),
    ("rss", "Ingeniería de Sistemas", "Google Noticias", GOOGLE),
]


def limpiar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def fecha_iso(valor: str | None) -> str | None:
    """Convierte la fecha de WordPress (hora de Colombia, sin zona), ISO 8601 o RFC 822 (RSS) a ISO con zona."""
    if not valor:
        return None
    valor = valor.strip()
    try:
        d = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=ZONA_CO)
        return d.isoformat()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(valor).isoformat()
    except (TypeError, ValueError):
        return None


def de_wordpress(texto: str, categoria: str, fuente: str) -> list[dict]:
    items = []
    for p in json.loads(texto):
        titulo = limpiar((p.get("title") or {}).get("rendered", ""))
        if titulo and p.get("link"):
            items.append(dict(titulo=titulo, url=p["link"], fecha=fecha_iso(p.get("date")), categoria=categoria,
                              resumen=limpiar((p.get("excerpt") or {}).get("rendered", ""))[:RESUMEN_MAX], fuente=fuente))
    return items


def de_rss(texto: str, categoria: str, fuente: str) -> list[dict]:
    items = []
    for it in ET.fromstring(texto.encode("utf-8")).iter("item"):
        titulo = limpiar(it.findtext("title"))
        url = (it.findtext("link") or "").strip()
        if not titulo or not url:
            continue
        medio = fuente
        origen = it.find("source")
        if origen is not None and (origen.text or "").strip():  # Google Noticias: "Titular - Medio"
            medio = limpiar(origen.text)
            titulo = re.sub(r"\s+-\s+" + re.escape(medio) + r"$", "", titulo)
            resumen = ""
        else:
            resumen = limpiar(it.findtext("description"))[:RESUMEN_MAX]
        items.append(dict(titulo=titulo, url=url, fecha=fecha_iso(it.findtext("pubDate")), categoria=categoria,
                          resumen=resumen, fuente=medio if medio == fuente else f"{medio} (vía {fuente})"))
    return items


def recolectar(retardo: float) -> list[dict]:
    vistos, salida = set(), []
    for tipo, categoria, fuente, url in FUENTES:
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            r.raise_for_status()
            r.encoding = r.encoding or "utf-8"
            nuevas = (de_wordpress if tipo == "wordpress" else de_rss)(r.text, categoria, fuente)
        except (requests.RequestException, ValueError, ET.ParseError) as e:
            print(f"[aviso] {fuente} ({categoria}) falló: {e}", file=sys.stderr)
            nuevas = []
        for n in nuevas[:10]:
            if n["url"] not in vistos:
                vistos.add(n["url"])
                salida.append(n)
        time.sleep(retardo)  # cortesía con los servidores
    salida.sort(key=lambda n: n["fecha"] or "", reverse=True)
    return salida


def es_de_hoy(n: dict) -> bool:
    if not n.get("fecha"):
        return False
    return datetime.fromisoformat(n["fecha"]).astimezone(ZONA_CO).date() == datetime.now(ZONA_CO).date()


def guardar(noticias: list[dict], database_url: str) -> int:
    import psycopg

    sql = """
    INSERT INTO noticias (titulo, url, fecha, categoria, resumen, fuente)
    VALUES (%(titulo)s, %(url)s, %(fecha)s, %(categoria)s, %(resumen)s, %(fuente)s)
    ON CONFLICT (url) DO UPDATE SET titulo = EXCLUDED.titulo, fecha = EXCLUDED.fecha,
      categoria = EXCLUDED.categoria, resumen = EXCLUDED.resumen, fuente = EXCLUDED.fuente
    """
    with psycopg.connect(database_url, prepare_threshold=None) as conn:  # compatible con el pooler de Supabase
        with conn.cursor() as cur:
            cur.executemany(sql, noticias)
        conn.commit()
    return len(noticias)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="imprimir JSON en lugar de escribir en la base de datos")
    ap.add_argument("--salida", help="archivo donde guardar el JSON (con --json)")
    ap.add_argument("--hoy", action="store_true", help="mostrar solo las noticias de hoy (hora de Colombia)")
    ap.add_argument("--retardo", type=float, default=1.5, help="segundos entre peticiones")
    args = ap.parse_args()

    noticias = recolectar(args.retardo)
    hoy = [n for n in noticias if es_de_hoy(n)]
    if args.hoy:
        print(f"Noticias del {datetime.now(ZONA_CO):%Y-%m-%d}: {len(hoy)} de {len(noticias)} recolectadas\n")
        for n in hoy:
            hora = datetime.fromisoformat(n["fecha"]).astimezone(ZONA_CO).strftime("%H:%M")
            print(f"[{n['categoria']}] {hora}  {n['titulo']}\n    Fuente: {n['fuente']}  {n['url'][:90]}")
        return 0
    meta = {"generado": datetime.now(timezone.utc).isoformat(timespec="seconds"), "total": len(noticias), "de_hoy": len(hoy)}
    if args.json:
        texto = json.dumps({"meta": meta, "noticias": noticias}, ensure_ascii=False, indent=2)
        if args.salida:
            with open(args.salida, "w", encoding="utf-8") as f:
                f.write(texto + "\n")
            print(f"{len(noticias)} noticias ({len(hoy)} de hoy) guardadas en {args.salida}")
        else:
            print(texto)
        return 0
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Falta DATABASE_URL (o use --json)", file=sys.stderr)
        return 2
    print(f"{guardar(noticias, url)} noticias insertadas/actualizadas ({len(hoy)} de hoy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
