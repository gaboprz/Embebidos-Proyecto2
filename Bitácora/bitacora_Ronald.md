# Bitácora de Desarrollo - Sistema de Diagnóstico Fitosanitario

**Proyecto:** Embebidos-Proyecto2 - Interfaz Web Multimodal  
**Estudiante:** Ronald Duarte  
**Periodo:** 22 de mayo - 25 de mayo, 2026  
**Repositorio:** git@github.com:gaboprz/Embebidos-Proyecto2.git

---

## Jueves 22 de mayo, 2026

### 14:00 - 16:00 | Análisis de Requisitos y Diseño de Arquitectura

**Actividades realizadas:**
- Definición de requisitos funcionales del sistema
- Especificación de tres modalidades de diagnóstico:
  - Modo imagen: análisis visual mediante carga de fotografías
  - Modo texto: análisis descriptivo de síntomas observados
  - Modo multimodal: combinación de imagen y descripción textual
- Selección de tecnologías:
  - Backend: FastAPI 0.104.1
  - Servidor ASGI: Uvicorn 0.24.0
  - Frontend: HTML5, CSS3, JavaScript ES6
  - Containerización: Docker + Docker Compose
  - Base de imágenes: Python 3.11-slim

**Decisiones arquitectónicas:**
- Arquitectura cliente-servidor REST
- Puerto de servicio: 8080
- Respuesta JSON con estructura estandarizada
- Tiempo de simulación: 2 segundos por diagnóstico

### 16:00 - 18:30 | Implementación del Backend

**Componentes desarrollados:**

Backend (main.py):
- Endpoint POST /diagnose: recepción de FormData multipart
- Endpoint GET /health: verificación de estado del servicio
- Endpoint GET /: servicio de archivos estáticos
- Función simulate_diagnosis(): generador de diagnósticos aleatorios
- Validación de entrada: al menos imagen o texto requerido
- Manejo de archivos con UploadFile de FastAPI

**Estructura de respuesta JSON:**
```json
{
  "enfermedad": "string",
  "confianza": "float (0-1)",
  "recomendacion": "string",
  "modalidad": "visual|textual|multimodal"
}
```

**Enfermedades en base de datos:**
- Sigatoka Negra (Mycosphaerella fijiensis)
- Sigatoka Amarilla (Mycosphaerella musicola)
- Fusarium / Mal de Panamá (Fusarium oxysporum)
- Deficiencia Nutricional
- Planta Sana

---

## Viernes 23 de mayo, 2026

### 09:00 - 12:00 | Desarrollo de Interfaz Frontend

**Componentes implementados:**

Interface web (index.html):
- Diseño responsive con CSS Grid y Flexbox
- Selector de modalidad con tres botones interactivos
- Zona de drag-and-drop para carga de imágenes
- Preview de imágenes antes de análisis
- Textarea para descripción de síntomas
- Botón de análisis con validación de entrada
- Área de resultados con animación de barra de confianza

**Estilos aplicados:**
- Fondo con gradiente lineal (667eea → 764ba2)
- Paleta de colores morada corporativa
- Transiciones CSS para interactividad
- Estados hover y active en botones
- Animación de carga durante procesamiento

**JavaScript implementado:**
- Event listeners para selección de modalidad
- Manejo de eventos drag-and-drop
- Preview de imágenes con FileReader API
- Validación de formulario por modalidad
- Petición fetch con FormData
- Renderizado dinámico de resultados
- Animación de barra de confianza con transiciones CSS

### 14:00 - 17:00 | Containerización con Docker

**Archivos de configuración creados:**

Dockerfile:
- Imagen base: python:3.11-slim
- Instalación de curl para healthchecks
- Copia de requirements.txt
- Instalación de dependencias Python sin cache
- Copia de código fuente (backend/ y static/)
- Exposición de puerto 8080
- CMD: python backend/main.py

docker-compose.yml:
- Servicio: banano-web
- Build context: directorio actual
- Port mapping: 8080:8080
- Network: banano-network (bridge driver)
- Restart policy: unless-stopped

requirements.txt:
- fastapi==0.104.1
- uvicorn==0.24.0
- python-multipart==0.0.6
- httpx==0.25.1
- pillow==10.1.0

**Pruebas realizadas:**
- Construcción de imagen Docker exitosa
- Inicio de contenedor en modo detached
- Verificación de logs: servidor Uvicorn activo
- Acceso a interfaz web en localhost:8080
- Pruebas de tres modalidades de diagnóstico

---

## Sábado 24 de mayo, 2026

### 10:00 - 13:00 | Resolución de Conflictos y Limpieza

**Problemas identificados:**
- Conflicto de puerto 8080 con contenedores OpenProject preexistentes
- Contenedor corrupto con ID f32ea3b9c66d
- Múltiples contenedores hello-world residuales

**Acciones correctivas:**
- Detención de servicios OpenProject (9 contenedores)
- Eliminación de contenedores hello-world redundantes
- Eliminación forzada de contenedor corrupto por ID
- Limpieza completa con docker container prune
- Verificación de puerto libre: netstat -tlnp | grep 8080

**Optimización del entorno:**
- Limpieza de imágenes huérfanas: docker image prune
- Limpieza de redes no utilizadas: docker network prune
- Limpieza de volúmenes sin referencia: docker volume prune
- Reconstrucción limpia de imagen banano-web

### 15:00 - 18:00 | Integración con Repositorio Git

**Configuración del repositorio:**
- Repositorio remoto: git@github.com:gaboprz/Embebidos-Proyecto2.git
- Copia de proyecto desde ~/Desktop/banano-web a ~/Documents/github/Embebidos-Proyecto2/banano-web

**Documentación creada:**

README.md:
- Descripción del proyecto
- Instrucciones de instalación
- Guía de uso de las tres modalidades
- Estructura del proyecto
- API endpoints documentados
- Tecnologías utilizadas
- Información del equipo

.gitignore:
- Archivos Python: __pycache__, *.pyc, venv/
- Datos Docker: data/
- IDEs: .vscode/, .idea/
- Sistema operativo: .DS_Store, Thumbs.db

**Commits realizados:**
feat: Add web interface for multimodal disease diagnosis

FastAPI backend with image/text/multimodal support
Responsive UI with drag-and-drop functionality
Docker containerization for easy deployment
Real-time diagnosis simulation
Support for 5 disease categories


---

## Domingo 25 de mayo, 2026

### 09:00 - 11:30 | Adaptación para Jetson Nano ARM64

**Archivos específicos para Jetson creados:**

Dockerfile.jetson:
- Imagen base compatible con ARM64
- Mismo stack de dependencias
- Optimizado para recursos limitados de Jetson

docker-compose.jetson.yml:
- Referencia a Dockerfile.jetson
- Configuración de red para comunicación con Ollama
- Variable de entorno: OLLAMA_HOST
- Extra hosts: host.docker.internal

INSTRUCCIONES_JETSON.md:
- Guía de instalación de Docker en Jetson Nano
- Comandos específicos para arquitectura ARM64
- Instrucciones de despliegue con docker-compose
- Comandos de administración y troubleshooting
- Configuración de firewall para puerto 8080

**Commit realizado:**
feat: Add Jetson Nano ARM64 support

Dockerfile.jetson for ARM64 architecture
docker-compose.jetson.yml for Jetson deployment
Complete setup instructions for Jetson Nano


### 13:00 - 15:30 | Configuración de Red y Conectividad

**Topología de red identificada:**
- PC (Gateway): IP 10.42.0.1
- Jetson Nano (Cliente): IP 10.42.0.203
- Red: 10.42.0.0/24
- Conexión: Ethernet o USB entre PC y Jetson

**Pruebas de conectividad:**
- Ping bidireccional PC ↔ Jetson: exitoso
- Verificación de puerto 8080 disponible
- Prueba de acceso HTTP desde PC a Jetson

**URLs de acceso documentadas:**
- Desde PC a Jetson: http://10.42.0.203:8080
- Desde PC (local): http://localhost:8080
- Desde dispositivos móviles en misma red: http://10.42.0.203:8080

### 16:00 - 18:00 | Implementación Sin Docker en Jetson

**Análisis de recursos:**
- Memoria RAM limitada en Jetson Nano
- Overhead de Docker: aproximadamente 500MB
- Overhead de Python directo: aproximadamente 150MB
- Decisión: implementación nativa más eficiente

**Procedimiento de instalación nativa:**

1. Instalación de dependencias del sistema:
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git
```

2. Clonación del repositorio:
```bash
git clone git@github.com:gaboprz/Embebidos-Proyecto2.git
cd Embebidos-Proyecto2/banano-web
```

3. Creación de entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Instalación de dependencias Python:
```bash
pip install -r requirements.txt
```

5. Ejecución del servidor:
```bash
python backend/main.py
```

**Configuración de servicio systemd:**

Archivo: /etc/systemd/system/banano-web.service
- Type: simple
- User: root
- WorkingDirectory: /root/Embebidos-Proyecto2/banano-web
- ExecStart: venv/bin/python backend/main.py
- Restart: always
- RestartSec: 10 segundos

**Comandos de administración del servicio:**
```bash
sudo systemctl enable banano-web    # Inicio automático
sudo systemctl start banano-web     # Iniciar servicio
sudo systemctl stop banano-web      # Detener servicio
sudo systemctl restart banano-web   # Reiniciar servicio
sudo systemctl status banano-web    # Ver estado
sudo journalctl -u banano-web -f    # Ver logs en tiempo real
```

**Alternativa con screen para ejecución en background:**
```bash
screen -S banano-web                # Crear sesión
python backend/main.py              # Ejecutar aplicación
# Ctrl+A, D                         # Desconectar sesión
screen -r banano-web                # Reconectar sesión
screen -ls                          # Listar sesiones
```

---

## Resumen Técnico del Proyecto

### Arquitectura del Sistema

**Capa de Presentación:**
- Interfaz web responsive HTML5/CSS3/JavaScript
- Tres modos de interacción: imagen, texto, multimodal
- Validación de entrada en cliente
- Animaciones CSS para feedback visual

**Capa de Aplicación:**
- API REST con FastAPI
- Endpoints: /, /diagnose, /health
- Procesamiento de FormData multipart
- Simulación de diagnóstico con respuestas aleatorias
- Tiempo de respuesta: 2 segundos

**Capa de Datos:**
- Base de conocimiento en memoria (diccionarios Python)
- 5 categorías de enfermedades
- Recomendaciones agronómicas específicas por enfermedad
- Confianza simulada: rango 75-98%

### Especificaciones de Despliegue

**Entorno de Desarrollo (PC):**
- Sistema operativo: Pop!_OS (Ubuntu-based)
- Docker Engine: versión 20.10+
- Docker Compose: versión 1.29+
- Puerto: 8080
- Acceso: http://localhost:8080

**Entorno de Producción (Jetson Nano):**
- Sistema operativo: Ubuntu 18.04/20.04 ARM64
- Python: 3.6+
- Entorno virtual: venv
- Puerto: 8080
- Acceso: http://10.42.0.203:8080
- Servicio systemd para ejecución continua

### Flujo de Datos

1. Usuario selecciona modalidad de diagnóstico
2. Cliente captura imagen y/o texto
3. JavaScript construye FormData y envía POST a /diagnose
4. Backend valida entrada (al menos imagen o texto)
5. Backend determina modalidad basado en datos recibidos
6. Backend ejecuta simulate_diagnosis()
7. Backend retorna JSON con diagnóstico
8. Cliente renderiza resultados con animación
9. Usuario visualiza enfermedad, confianza y recomendaciones

### Métricas del Proyecto

**Líneas de código:**
- Backend (Python): aproximadamente 120 líneas
- Frontend (HTML/CSS/JS): aproximadamente 400 líneas
- Configuración (Docker, compose): aproximadamente 50 líneas

**Archivos del proyecto:**
- Código fuente: 3 archivos principales
- Configuración: 5 archivos
- Documentación: 4 archivos

**Dependencias:**
- Python: 5 paquetes principales + 15 transitorias
- Sistema: curl, git, python3

### Trabajo Futuro

**Integración con Ollama:**
- Reemplazo de simulate_diagnosis() con llamada HTTP a Ollama
- Endpoint: http://localhost:11434/api/generate
- Modelo: LLaVA (visión + lenguaje)
- Conversión de imagen a base64
- Construcción de prompt combinando imagen y texto

**Base de datos SQLite:**
- Tabla de diagnósticos históricos
- Campos: timestamp, modalidad, imagen_path, texto, resultado
- Endpoint /history para consulta de historial
- Análisis estadístico de diagnósticos

**Visualización Grad-CAM:**
- Overlay de mapa de activación en imagen
- Resaltado de regiones relevantes para diagnóstico
- Explicabilidad del modelo

**Optimizaciones:**
- Cache de resultados para imágenes duplicadas
- Compresión de imágenes antes de procesamiento
- Rate limiting para prevenir abuso
- Autenticación básica HTTP

---

## Conclusiones

El proyecto alcanzó los objetivos establecidos:

1. Sistema funcional con tres modalidades de entrada implementadas
2. Interfaz web responsive y visualmente atractiva
3. Backend RESTful con arquitectura escalable
4. Despliegue exitoso en dos plataformas (PC x86_64 y Jetson Nano ARM64)
5. Documentación completa para replicación
6. Código versionado en GitHub para colaboración del equipo

El sistema está preparado para la integración con modelos de IA reales (Ollama/LLaVA) y puede servir como plataforma base para investigación en diagnóstico fitosanitario asistido por computadora.

**Total de horas invertidas:** Aproximadamente 28 horas
**Estado del proyecto:** Prototipo funcional completado
**Próximos pasos:** Integración con modelo de IA y pruebas de campo

---

**Elaborado por:** Ronald Duarte  
**Fecha de elaboración:** 25 de mayo, 2026  
**Versión del documento:** 1.0
EOF

echo "Bitácora creada: BITACORA_PROYECTO.md"
Ahora agrégala al repositorio:
bash# Agregar a git
git add BITACORA_PROYECTO.md

# Commit
git commit -m "docs: Add project development log (bitacora)

- Detailed timeline from May 22-25, 2026
- Technical specifications and decisions
- Architecture documentation
- Deployment procedures for PC and Jetson
- Future work roadmap"

# Push
git push origin main
