# KFC Order Management Bot

Bot de Telegram para la gestión y auditoría de órdenes de KFC, con funcionalidades de re-impresión y seguimiento de motorizados.

## Características

- ✅ Verificación de estado de órdenes con información de motorizados
- ✅ Auditoría completa de órdenes
- ✅ Generación de imágenes de facturas y comandas
- ✅ Sistema de re-impresiones con límites configurables
- ✅ Logs estructurados por año/mes/día
- ✅ Conexiones a base de datos con timeout automático
- ✅ Interfaz intuitiva con menús inline
- ✅ Dockerizado para despliegue en AKS

## Estructura del Proyecto
kfc_order_management_bot/
├── src/ # Código fuente
├── logs/ # Logs estructurados
├── docker/ # Configuración Docker
├── tests/ # Tests unitarios
└── data/ # Datos temporales


## Configuración

1. Copiar `.env.example` a `.env`
2. Configurar las variables de entorno:
   - `BOT_TOKEN`: Token del bot de Telegram
   - Credenciales de base de datos
   - Configuraciones de logging

## Despliegue con Docker

```bash
# Construir la imagen
docker-compose build

# Ejecutar en producción
docker-compose up -d

# Ver logs
docker-compose logs -f kfc-bot