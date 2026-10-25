"""
Función Lambda disparada por Amazon S3 (Escenario A).

Cada vez que se sube un archivo al bucket configurado como trigger,
S3 envía un evento a esta función. La función lee los datos del evento,
consulta los metadatos del archivo y escribe en CloudWatch Logs:
    Archivo procesado: <nombre-del-archivo>
"""

import json
import logging
import urllib.parse

import boto3
from botocore.exceptions import ClientError

# Logger: todo lo que se registra aquí aparece en CloudWatch Logs
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente de S3 creado fuera del handler para reutilizarlo entre invocaciones
s3 = boto3.client("s3")


def lambda_handler(event, context):
    procesados = []

    # Un evento de S3 puede traer uno o varios registros (Records)
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        # S3 codifica el nombre en el evento (espacios como "+", tildes como %XX)
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        # Mensaje pedido por la consigna
        logger.info("Archivo procesado: %s", key)

        # Lectura de metadatos: requiere el permiso s3:GetObject del rol
        try:
            meta = s3.head_object(Bucket=bucket, Key=key)
            logger.info(
                "Detalle -> bucket: %s | tamaño: %s bytes | tipo: %s",
                bucket,
                meta.get("ContentLength"),
                meta.get("ContentType"),
            )
        except ClientError as error:
            # Si falta el permiso, el error queda registrado en CloudWatch
            logger.error("No se pudo leer %s en %s: %s", key, bucket, error)
            raise

        procesados.append(key)

    return {
        "statusCode": 200,
        "body": json.dumps({"archivos_procesados": procesados}, ensure_ascii=False),
    }
