## **Fecha: 19/05/26**

- se buscan modelos para el entrenamiento y que cumplan con los requisitos del proyecto.
- Se encuentra modelo ViT compatible con Jetson Nano 
- Se busca set datos para entrenar

### Problemas

- El set de datos encontrado solo tiene un tipo de enfermedad y hoja sana, por lo que no se cumplirian los requisitos en cuanto a las enfermedades existentes en Costa Rica.

## **Fecha: 23/05/26**

- Se busca otro modelo que se compatible con la Jetson y que sea compatible para TensorRT
- Se encentran opciones de modelo para la implementacion del train
    1. MobileNetV2 
    2. EfficientNetB0
    3. ResNet18
- De los modelos encontrados se investiga su  compatibilidad con ollama y finalmente se decide usar MobileNetV2.
- Se busca nuevo set de datos y se encuentra un nuevo set en [Kaggle](https://www.kaggle.com/datasets/sujaykapadnis/banana-disease-recognition-dataset), donde tambien se encuentra un el codigo de train que usa como modelo MobileNetV3, por lo que se utiliza como codigo base para el codigo de entrenamiento, pero modificandolo para que use MobileNetV2.
- Se procede hacer el entrenamiento
- 
### Errores / Problemas

- Se tienen problemas para iniciar sesion en wandb
- Se tienen errores para encontrar la ubicacion del set de datos

### Solucion

- Se cambia el API Key de wandb y se logra acceder a wandb
- Se busca la ubicacion del set de datos y se logra iniciar con el entrenamiento

## **Fecha: 24/05/26**

- Se ajustan los parametros de entrenamiento porque de acuerdo a las metricas registradas de observa que el modelo esta confundiendo las enfermedades en especial la Sigatoka amarrilla y la de Panama debido a que tienen muy pocos datos para entrenar, por lo que se procede ajustar parametros de entrenamiento.
- Se consigue una mejora en el entrenamiento por lo que se procede a hacer la inferencia
- Se exporta el modelo a formato ONNX para utilizar en el Jetson Nano
  
### Errores / Problemas

- Se tiene problemas al exportar el modelo, por lo que se revisa el script ``export_onnx.py`` y se logra exportar con exito.
- Se hace el test de inferencia del modelo ``.onnx`` y se detecta que hay mucha confusion a la hora de clasificar enfermedades.
- Se entrena nuevamente el modelo ``.pt`` 
- Se exporta el nuevo modelo a formato ONNX, y se decide conservar este ultimo, se logro mejorar la clasificacion de enfermedades.
- Se decide no entrenar mas porque el set de datos es muy pequeño, por lo que ya se esta llegan a ver un peque;o sobre ajuste del modelo.

## **Fecha: 25/05/26**

- Se convierte el modelo a .tar para poder hacer la imagen en yocto
  

## Recomendaciones.

```
El set de datos usado es muy pequeño, en total se tiene 217 imagen, sin embargo, la cantidad de imagenes no es equitativa, por lo que el modelo se puede mejorar si se tiene un set de datos mas grande. 
Por como esta ahorita el modelo, no es recomendable seguir entrenando porque se va a llegar a un sobre ajuste y esto seria un gran problema cuando se requiera clasificar imagenes nuevas.
```