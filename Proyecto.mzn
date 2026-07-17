% ADA 2 - PROYECTO 2: MINIMIZAR LA POLARIZACIÓN PRESENTE EN UNA POBLACIÓN

% AUTORES:
% DANIEL ARIAS CASTRILLÓN - 202222205 
% VENUS PAIPILLA - 202343803
% NICOLAS ENRIQUE GRANADA FERNANDEZ - 202310107 

% --- Parámetros de Entrada ---
int: n; % Número total de personas en la población
int: m; % Número de opiniones posibles

array[1..m] of int: p;        % Distribución inicial de personas por opinión
array[1..m] of float: v;      % Valores reales de cada opinión (v1 < v2 < ... < vm)
array[1..m] of float: ce;     % Costos extras de desplazamientos a opiniones inicialmente vacías (p[j] == 0)
array[1..m, 1..m] of float: c; % Matriz de costos de desplazamiento de opinión i a j

float: ct;     % Costo total máximo permitido
int: MaxMovs; % Máximo número de movimientos permitidos (distancia acumulada |j - i|)

% --- Escalado a Enteros (para evitar errores de límites de punto flotante en Gecode) ---
int: scale = 10000; % Factor de escala para preservar precisión de 4 decimales

array[1..m] of int: scaled_v = [ round(v[i] * int2float(scale)) | i in 1..m ];
array[1..m] of int: scaled_ce = [ round(ce[i] * int2float(scale)) | i in 1..m ];
array[1..m, 1..m] of int: scaled_c = array2d(1..m, 1..m, [
    round(c[i, j] * int2float(scale)) | i, j in 1..m
]);

% Multiplicamos el presupuesto ct por la escala y por n para eliminar la división por n de la restricción de costo
int: scaled_ct_times_n = round(ct * int2float(scale) * int2float(n));

% Coeficientes de costos de transición pre-calculados (enteros puros)
% Para p[j] > 0: c[i,j] * (n + p[i])
% Para p[j] == 0: c[i,j] * (n + p[i]) + ce[j] * n
array[1..m, 1..m] of int: cost_coeff = array2d(1..m, 1..m, [
    if j == i then 0
    else if p[j] > 0 then
        scaled_c[i, j] * (n + p[i])
    else
        scaled_c[i, j] * (n + p[i]) + scaled_ce[j] * n
    endif endif
    | i, j in 1..m
]);

% --- Variables de Decisión ---
% x[i, j] representa el número de personas que pasan de la opinión i a la opinión j
array[1..m, 1..m] of var int: x;

% --- Restricciones Básicas (Enteras) ---

% 1. No negatividad
constraint forall(i in 1..m, j in 1..m) (
    x[i, j] >= 0
);

% 2. Conservación del flujo de salida
constraint forall(i in 1..m) (
    sum(j in 1..m) (x[i, j]) = p[i]
);

% 3. Distribución final resultante de personas por opinión
array[1..m] of var int: p_final = [ sum(i in 1..m) (x[i, j]) | j in 1..m ];

% 4. Restricción del límite de movimientos (distancia total recorrida)
constraint sum(i in 1..m, j in 1..m) (
    x[i, j] * abs(j - i)
) <= MaxMovs;

% 5. Presupuesto (Lineal y Entero Puro)
var int: scaled_cost = sum(i in 1..m, j in 1..m where j != i) (
    cost_coeff[i, j] * x[i, j]
);
constraint scaled_cost <= scaled_ct_times_n;

% --- Modelado Lineal Entero de la Mediana ---
% z[k] es 1 si la opinión v[k] es seleccionada como la mediana final, 0 de lo contrario
array[1..m] of var bool: z;
constraint sum(k in 1..m) (bool2int(z[k])) = 1;

var 1..m: med_idx = sum(k in 1..m) (k * bool2int(z[k]));

% Restricciones de mediana condicionales lineales (usando div entero en vez de ceil float)
int: half_pop = (n + 1) div 2;

constraint forall(k in 1..m) (
    sum(i in 1..k) (p_final[i]) >= half_pop - n * (1 - bool2int(z[k]))
);

constraint forall(k in 1..m) (
    sum(i in k..m) (p_final[i]) >= half_pop - n * (1 - bool2int(z[k]))
);

% --- Linealización Entera de la Función Objetivo ---
% w[i, k] representa la variable linealizada que sustituye al producto p_final[i] * z[k]
array[1..m, 1..m] of var int: w;

constraint forall(i in 1..m, k in 1..m) (
    w[i, k] >= 0 /\
    w[i, k] <= n * bool2int(z[k]) /\
    w[i, k] <= p_final[i] /\
    w[i, k] >= p_final[i] - n * (1 - bool2int(z[k]))
);

% Matriz de distancias absolutas escaladas a enteros
array[1..m, 1..m] of int: scaled_dist = array2d(1..m, 1..m, [
    abs(scaled_v[i] - scaled_v[j]) | i, j in 1..m
]);

% Función Objetivo (Suma ponderada entera pura)
var int: scaled_polarization = sum(i in 1..m, k in 1..m) (
    w[i, k] * scaled_dist[i, k]
);

solve minimize scaled_polarization;

% --- Formato de Salida (Calculado sobre enteros fijos) ---
output [
    "polarization = ", show(int2float(fix(scaled_polarization)) / int2float(scale)), ";\n",
    "med_idx = ", show(med_idx), ";\n",
    "med_val = ", show(v[fix(med_idx)]), ";\n",
    "p_final = ", show(p_final), ";\n",
    "x = ", show(x), ";\n",
    "total_cost = ", show(int2float(fix(scaled_cost)) / (int2float(scale) * int2float(n))), ";\n",
    "total_movs = ", show(sum(i in 1..m, j in 1..m) (x[i, j] * abs(j - i))), ";\n"
];
