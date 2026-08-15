# Imagen fijada, no "python:3.12" ni "python:slim".
#
# Tu laptop corre una versión de Python y el contenedor corre otra: ahí vive el "anda en mi
# máquina". 3.12-slim es la de cobertura de ruedas más ancha y la de más reposo, así que nada
# se compila desde fuente y no hace falta toolchain.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Las dependencias primero y solas. Mientras requirements.txt no cambie, esta capa se reusa y
# el despliegue no vuelve a bajar todo.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Si quedó un .env en el árbol, no viaja adentro de la imagen. Una credencial escrita en una
# capa sobrevive al borrado: sale entera con `docker history`. Los valores los inyecta la
# plataforma, o van por --env-file cuando corrés local.
RUN rm -f .env .env.*

# Sin privilegios. El proceso solo escribe en /app, y ahí lo dejamos.
RUN useradd --create-home --uid 10001 agente && chown -R agente:agente /app
USER agente

# Dos cosas que parecen detalle y no lo son.
#
# Forma shell (sh -c), no forma exec con el puerto escrito a mano: Railway inyecta PORT y el
# valor cambia entre despliegues. Con el puerto fijo la app escucha en otro lado, el healthcheck
# no contesta nunca y lo único que vas a leer es "service unavailable", sin un error útil.
# ${PORT:-8000} lo resuelve el shell al arrancar, y en local sin PORT queda 8000.
#
# exec: sin él el shell se queda de PID 1, se come el SIGTERM y uvicorn no se entera de que lo
# están apagando. La plataforma espera, no pasa nada, y termina matando el proceso a la fuerza.
# Con exec, uvicorn ES el PID 1 y recibe la señal.
CMD ["sh","-c","exec uvicorn agente.servidor:app --host 0.0.0.0 --port ${PORT:-8000}"]
