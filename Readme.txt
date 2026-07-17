ADA 2 - PROYECTO 2: MINIMIZAR LA POLARIZACIÓN PRESENTE EN UNA POBLACIÓN


AUTORES:
DANIEL ARIAS CASTRILLÓN - 202222205 
VENUS PAIPILLA - 202343803
NICOLAS ENRIQUE GRANADA FERNANDEZ - 202310107 

REQUISITOS DEL SISTEMA

1. Python 3.8 o superior.
   * La aplicación utiliza ÚNICAMENTE librerías estándar integradas (tkinter, subprocess, os, shutil, re, glob, time).
2. MiniZinc 2.8 o superior.
   * Se puede descargar desde el sitio web oficial: https://www.minizinc.org/software.html

INSTRUCCIONES DE EJECUCIÓN

1. Extraer los archivos del comprimido .zip.
2. Navegar hasta la carpeta 'ProyectoGUIFuentes'.
3. Ejecutar el comando:
   python gui.py
4. Una vez abierta la interfaz gráfica:
   - Se intentará detectar automáticamente la ruta de 'minizinc.exe'. Si no se encuentra (se mostrará en rojo), presione el botón "Buscar minizinc.exe Manualmente" y seleccione el ejecutable de su instalación local de MiniZinc.
   - Presione el botón "Cargar Instancia (.mpl)" o use el menú superior "Archivo -> Cargar archivo .mpl" para cargar cualquiera de las instancias de prueba de la carpeta 'bateria_pruebas/mpl' o 'MisInstancias'.
   - Puede ver y editar los parámetros generales, la distribución y los costos de transición en las tablas interactivas.
   - Presione el botón azul "EJECUTAR SOLVER (MiniZinc)". Esto generará el archivo 'DatosProyecto/DatosProyecto.dzn' y llamará a MiniZinc con el solver Gecode.
   - Los resultados de la polarización óptima, opinión mediana, costos, movimientos y transiciones de población detalladas se mostrarán de inmediato en la pantalla.

