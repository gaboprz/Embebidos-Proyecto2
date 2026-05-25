# Instrucciones para Jetson Nano

## Requisitos Previos
- Jetson Nano con Ubuntu 18.04/20.04
- Docker instalado
- Docker Compose instalado
- Git instalado

## Instalación de Docker (si no está instalado)

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Agregar usuario al grupo docker
usermod -aG docker $USER

# Instalar Docker Compose
apt-get install -y docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

## Despliegue de la Aplicación

```bash
# 1. Clonar el repositorio
git clone git@github.com:gaboprz/Embebidos-Proyecto2.git
cd Embebidos-Proyecto2/banano-web

# 2. Construir e iniciar
docker-compose -f docker-compose.jetson.yml up -d --build

# 3. Ver logs
docker logs -f banano-web

# Debería ver:
# INFO:     Uvicorn running on http://0.0.0.0:8080
```

## Acceso a la Aplicación

```bash
# Averiguar IP de la Jetson
hostname -I | awk '{print $1}'

# Desde otro dispositivo en la misma red:
# http://<IP_JETSON>:8080
# Ejemplo: http://10.42.0.203:8080
```

## Comandos Útiles

```bash
# Ver logs en tiempo real
docker logs -f banano-web

# Detener
docker-compose -f docker-compose.jetson.yml down

# Reiniciar
docker-compose -f docker-compose.jetson.yml restart

# Reconstruir después de cambios
docker-compose -f docker-compose.jetson.yml up -d --build

# Ver contenedores corriendo
docker ps

# Ver uso de recursos
docker stats banano-web
```

## Verificación de Puerto

```bash
# Verificar que el puerto 8080 está escuchando
netstat -tlnp | grep 8080

# Si hay firewall, permitir puerto
ufw allow 8080
```

## Troubleshooting

### Puerto ocupado
```bash
netstat -tlnp | grep 8080
kill <PID>
```

### Contenedor no inicia
```bash
docker logs banano-web
```

### Reconstruir desde cero
```bash
docker-compose -f docker-compose.jetson.yml down -v
docker-compose -f docker-compose.jetson.yml up -d --build
```

### Actualizar código desde GitHub
```bash
cd ~/Embebidos-Proyecto2/banano-web
git pull origin main
docker-compose -f docker-compose.jetson.yml up -d --build
```

## Arquitectura

- **Sistema:** Ubuntu 18.04/20.04 ARM64
- **Python:** 3.11-slim
- **Backend:** FastAPI + Uvicorn
- **Puerto:** 8080
- **Red:** Bridge (banano-network)

## Equipo

- Gabriel Pérez - Líder Técnico
- Katherine Salazar - Directora de Proyecto
- Ronald Duarte - Investigador

Proyecto académico - Tecnológico de Costa Rica
