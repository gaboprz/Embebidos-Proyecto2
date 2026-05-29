# 🍌 Banano Web - Interfaz de Diagnóstico Fitosanitario

Sistema web para reconocimiento de enfermedades en cultivos de banano mediante IA.

## 🚀 Inicio Rápido

### Requisitos
- Docker
- Docker Compose

### Instalación y Ejecución

```bash
# 1. Clonar el repositorio
git clone git@github.com:gaboprz/Embebidos-Proyecto2.git
cd Embebidos-Proyecto2/banano-web

# 2. Construir y correr
docker-compose up -d

# 3. Abrir en navegador
http://localhost:8080
```

## 🎯 Funcionalidades

### Modalidades de Diagnóstico

1. **📷 Solo Imagen**: Sube una foto de la hoja
2. **✍️ Solo Texto**: Describe los síntomas observados  
3. **🔄 Multimodal**: Combina imagen + descripción textual

### Enfermedades Detectables

- Sigatoka Negra (*Mycosphaerella fijiensis*)
- Sigatoka Amarilla (*Mycosphaerella musicola*)
- Fusarium / Mal de Panamá (*Fusarium oxysporum*)
- Deficiencias Nutricionales
- Planta Sana

## 🛠️ Comandos Útiles

```bash
# Ver logs
docker logs -f banano-web

# Detener
docker-compose down

# Reconstruir
docker-compose up -d --build

# Entrar al contenedor
docker exec -it banano-web bash
```

## 🏗️ Estructura
banano-web/
├── backend/
│   └── main.py          # API FastAPI
├── static/
│   └── index.html       # Interfaz web
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

## 📊 API Endpoints

- `GET /` - Interfaz web
- `POST /diagnose` - Diagnóstico multimodal
- `GET /health` - Estado del servidor

## 👥 Equipo

- Gabriel Pérez - Líder Técnico
- Katherine Salazar - Directora de Proyecto
- Ronald Duarte - Investigador

Proyecto académico - Tecnológico de Costa Rica 🇨🇷
