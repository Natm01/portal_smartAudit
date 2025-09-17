SmartAudit Proto API
======================

API FastAPI con Python 3.11 para el portal SmartAudit, desplegada en Azure Container Apps.

**URL Base**: `https://{env}smartaudit.granthornton.es/smau-proto-api/`

# Estructura del Proyecto
```
api/
├── main.py                   # FastAPI application
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container configuration
├── pytest.ini                # Test configuration
├── azure-pipelines-api.yml   # CI/CD pipeline
├── tests/                    # Test files
│   └── test_main.py
└── README.md                 # This file
```

# Desarrollo Local

## Requisitos
- Python 3.11+
- Docker (opcional)
- Azure CLI (para deployment)

## Setup rápido

### 1 Instalar dependencias

```bash
cd api

# python -m venv venv  Ejecutar este comando si no está creado el virtual environment

venv\Scripts\activate  # Windows

python -m pip install --upgrade pip

pip install -r requirements.txt
```

### 2.A) Ejecutar API Local

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2.B) Ejecutar API Con Docker

```bash
# Desde el directorio api/
docker build -t smau-dev-portal-web-proto-api .
docker run -p 8000:8000 smau-dev-portal-web-proto-api

# O usando docker-compose desde root del proyecto
docker-compose up api
```

## Probar API Local 

curl --location 'http://localhost:8000/health/ready'
```json
{
    "status": "healthy",
    "timestamp": "2025-09-02T08:57:05.956464Z",
    "version": "1.0.0",
    "environment": "development"
}
```

## Endpoints Principales

### Health & Status
- `GET /smau-proto-api/` - Información básica de la API
- `GET /smau-proto-api/health` - Health check
- `GET /smau-proto-api/version` - Información de versión
- `GET /smau-proto-api/test-connection` - Test de conectividad

### Items CRUD (Ejemplo)
- `GET /smau-proto-api/items` - Listar todos los items
- `GET /smau-proto-api/items/{id}` - Obtener item específico
- `POST /smau-proto-api/items` - Crear nuevo item
- `PUT /smau-proto-api/items/{id}` - Actualizar item
- `DELETE /smau-proto-api/items/{id}` - Eliminar item

### Documentación Interactiva
- `/smau-proto-api/docs` - Swagger UI
- `/smau-proto-api/redoc` - ReDoc

## Testing

```bash
# Ejecutar todos los tests
pytest tests/ -v

# Con coverage
pytest tests/ -v --cov=.

# Solo tests específicos
pytest tests/test_main.py::TestHealthEndpoints -v
```

## Configuración CORS

La API está configurada para permitir requests desde:
- https://devapi.grantthornton.es
- https://testapi.grantthornton.es
- https://api.grantthornton.es
- https://devsmartaudit.grantthornton.es
- https://testsmartaudit.grantthornton.es 
- https://smartaudit.grantthornton.es 
- http://localhost:3000 (Desarrollo local React)
- http://localhost:4280 (Desarrollo local SWA)

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Entorno de ejecución | `development` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

## Deployment

### Azure Container Apps

El deployment se realiza automáticamente mediante Azure Pipelines:

1. **Push a `dev`** → Deploy a `smartaudit-proto-api-ca-dev`
2. **Push a `main`** → Deploy a `smartaudit-proto-api-ca-prod`

### Manual Deployment

```bash
# Build y push imagen
az acr build --registry itdevtestregister --image smau-dev-portal-web-proto-api:latest .

# Update Container App
az containerapp update \
  --name smau-dev-proto-api-container \
  --resource-group smau-dev-rg \
  --image itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest


az containerapp update --name smau-dev-proto-api-container --resource-group smau-dev-rg --image itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest


# Con docker
# docker login itdevtestregister.azurecr.io
# username: itdevtestregister
# pwd: uL...HlW

docker build -t itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest .
docker push itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest

az containerapp update --name smau-dev-proto-api-container --resource-group smau-dev-rg --image itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest


https://devapi.grantthornton.es/smau-proto-api/health

```

## Monitoreo

### Health Checks
- Container Apps realiza health checks automáticos en `/smau-proto-api/health`
- Intervalo: 30 segundos
- Timeout: 10 segundos

### Logs
```bash
# Ver logs en tiempo real
az containerapp logs show --name smartaudit-proto-api-ca-prod --resource-group smartaudit-rg --follow

# Logs específicos
az monitor log-analytics query \
  --workspace smartaudit-logs \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'smartaudit-proto-api-ca-prod'"
```

### Métricas Importantes
- Response time promedio: < 500ms
- Error rate: < 1%
- Memory usage: < 500MB
- CPU usage: < 70%

## Troubleshooting

### Problemas Comunes

**CORS Errors**
```python
# Verificar configuración en main.py
ALLOWED_ORIGINS = [
    "https://dev.smartaudit.com",
    # ...
]
```

**Container no inicia**
```bash
# Revisar logs
az containerapp logs show --name smartaudit-proto-api-ca-prod --resource-group smartaudit-rg

# Verificar health endpoint
curl https://dev.smartaudit.com/smau-proto-api/health
```

**Performance Issues**
```bash
# Revisar métricas de container
az containerapp show --name smartaudit-proto-api-ca-prod --resource-group smartaudit-rg --query "properties.template.containers[0].resources"
```

# Desarrollo

## Agregar nuevo endpoint

```python
@app.get("/smau-proto-api/nuevo-endpoint")
async def nuevo_endpoint():
    return {"message": "Nuevo endpoint"}
```

## Agregar tests

```python
def test_nuevo_endpoint():
    response = client.get("/smau-proto-api/nuevo-endpoint")
    assert response.status_code == 200
```

## Hot reload para desarrollo
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

# Contacto y Soporte

Para issues relacionados con la API:
1. Revisar logs en Azure Monitor
2. Ejecutar health check endpoints
3. Verificar configuración CORS
4. Contactar al equipo de desarrollo




az containerapp exec --name smau-dev-proto-api-container --resource-group smau-dev-rg --command "/bin/bash"

az containerapp logs show --name smau-dev-proto-api-container --resource-group smau-dev-rg --follow

# O logs específicos del contenedor
az containerapp logs show \
  --name smau-dev-proto-api-container \
  --resource-group smau-dev-rg \
  --container pythonprotoapi \
  --follow




**Alternativas más confiables para testing:**

**1. Logs del Container App (más útil para debugging):**
```bash
az containerapp logs show --name smau-dev-proto-api-container --resource-group smau-dev-rg --follow

# O logs específicos del contenedor
az containerapp logs show --name smau-dev-proto-api-container --resource-group smau-dev-rg --container pythonprotoapi --follow
```

**2. Test directo de la API (recomendado):**
```bash
# Obtener URL pública
APP_URL=$(az containerapp show --name smau-dev-proto-api-container --resource-group smau-dev-rg --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Container App URL: https://$APP_URL"

# Test endpoints
curl -v https://smau-dev-proto-api-container.livelybay-05e87ca2.westeurope.azurecontainerapps.io/health
curl -v https://$APP_URL/docs
curl -v https://$APP_URL/
```

**3. Verificar estado del Container App:**
```bash
az containerapp revision list \
  --name smau-dev-proto-api-container \
  --resource-group smau-dev-rg \
  --query "[].{Name:name, Status:properties.runningState, Replicas:properties.replicas}" \
  --output table


az containerapp revision list --name smau-dev-proto-api-container --resource-group smau-dev-rg --query "[].{Name:name, Status:properties.runningState, Replicas:properties.replicas}" --output table

```

El testing directo via HTTP es más confiable que `exec` para validar que tu FastAPI funciona correctamente. Los logs te darán información detallada si hay errores de arranque o runtime.  





# Despliegues

```bash
# Local
docker build -t smau-dev-portal-web-proto-api .
docker run -p 8000:8000 smau-dev-portal-web-proto-api

# Verificar health endpoint
curl http://localhost:8000/smau-proto/health

# Push al register

docker build -t itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest .
docker push itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest

# Update App Container
az containerapp update --name smau-dev-proto-api-container --resource-group smau-dev-rg --image itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest


az containerapp revision set-mode --name smau-dev-proto-api-container --resource-group smau-dev-rg --mode single 

  
az containerapp update \
  --name smau-dev-proto-api-container \
  --resource-group smau-dev-rg \
  --image itdevtestregister.azurecr.io/smau-dev-portal-web-proto-api:latest \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.25 \
  --memory 0.5Gi



# Ver logs inmediatamente
az containerapp logs show --name smau-dev-proto-api-container --resource-group smau-dev-rg --tail 50

# Fix rápido con puerto correcto
az containerapp update \
  --name smau-dev-proto-api-container \
  --resource-group smau-dev-rg \
  --target-port 8000 \
  --env-vars ENVIRONMENT=development PYTHONUNBUFFERED=1 PORT=8000


https://smau-dev-proto-api-container.livelybay-05e87ca2.westeurope.azurecontainerapps.io
smau-dev-proto-api-container.livelybay-05e87ca2.westeurope.azurecontainerapps.io
```


# Diagnóstico de time outs
## 1. Ver configuración actual de ingress
```
az containerapp show --name smau-dev-proto-api-container --resource-group smau-dev-rg --query "properties.configuration.ingress" --output table
```
## 2. Ver uso de recursos actual
```
az containerapp show --name smau-dev-proto-api-container --resource-group smau-dev-rg --query "properties.template.{cpu:containers[0].resources.cpu, memory:containers[0].resources.memory}" --output table
```
## 3. Ver logs de timeout
```
az containerapp logs show --name smau-dev-proto-api-container --resource-group smau-dev-rg --tail 50 | grep -i timeout
```


# Aumentando recursos

# Solución rápida de timeout - aumentar recursos y configurar timeouts

az containerapp update --name smau-dev-proto-api-container --resource-group smau-dev-rg --cpu 1.0 --memory 2Gi

# Test inmediato
```
curl -w "Total time: %{time_total}s\n" -o /dev/null -s https://testapi.grantthornton.es/smau-proto/

curl -l 'https://testapi.grantthornton.es/smau-proto/'
curl -l 'https://testapi.grantthornton.es/smau-proto/items'
curl -l 'https://testapi.grantthornton.es/smau-proto/health'


curl -l 'http://localhost:8000/smau-proto/'
curl -l 'http://localhost:8000/health/ready'
curl -l 'http://localhost:8000/smau-proto/test-connection'
```


# Comprobar variables de entorno

## Ver variables de entorno en el container
```
az containerapp exec --name smau-dev-proto-api-container --resource-group smau-dev-rg --command env | grep -E "(APP_VERSION|BUILD_ID|IMAGE_TAG)"
```
## Test del endpoint
```
curl -l https://devapi.grantthornton.es/smau-proto/health
```