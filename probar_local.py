"""
Ejecuta lambda_handler en tu computadora, usando un evento simulado de S3.

Sirve para probar cambios en segundos, sin desplegar en AWS.

Modos:
    python probar_local.py             # simulado: no usa AWS ni credenciales
    python probar_local.py --error     # simulado: S3 responde 403 (falta s3:GetObject)
    python probar_local.py --real      # real: llama a S3 con tus credenciales de AWS

Requisitos: Python 3.9+ y boto3 (pip install boto3).
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Región por defecto, para poder crear el cliente de S3 sin configuración previa
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# Muestra en la terminal lo mismo que Lambda envía a CloudWatch
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)

import lambda_function  # noqa: E402  (se importa después de fijar la región)

EVENTO = Path(__file__).parent / "eventos" / "evento_prueba_s3.json"


def main():
    parser = argparse.ArgumentParser(description="Prueba local de la función Lambda")
    parser.add_argument("--real", action="store_true", help="llamar a S3 de verdad")
    parser.add_argument("--error", action="store_true", help="simular el error de permisos (403)")
    args = parser.parse_args()

    event = json.loads(EVENTO.read_text(encoding="utf-8"))
    record = event["Records"][0]["s3"]
    bucket, key = record["bucket"]["name"], record["object"]["key"]
    print(f"Evento simulado: archivo '{key}' en el bucket '{bucket}'\n")

    if args.real:
        resultado = lambda_function.lambda_handler(event, None)
        print("\nRespuesta:", resultado)
        return

    # Modo simulado: reemplaza la respuesta de S3 sin salir a internet
    from botocore.stub import Stubber
    from botocore.exceptions import ClientError

    stubber = Stubber(lambda_function.s3)
    if args.error:
        stubber.add_client_error("head_object", service_error_code="403",
                                 service_message="Forbidden", http_status_code=403)
    else:
        stubber.add_response("head_object",
                             {"ContentLength": record["object"].get("size", 0),
                              "ContentType": "text/plain"},
                             {"Bucket": bucket, "Key": key})

    with stubber:
        try:
            resultado = lambda_function.lambda_handler(event, None)
            print("\nRespuesta:", resultado)
        except ClientError:
            print("\nLa función relanzó el error, igual que en AWS: la invocación queda marcada como fallida.")


if __name__ == "__main__":
    main()
